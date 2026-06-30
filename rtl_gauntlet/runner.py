"""Orchestrate the two-tier evaluation of one pilot task.

Flow (ADR-0001): agent produces RTL against VISIBLE diagnostics → freeze it →
score the withheld tiers it never saw: HIDDEN randomized/exhaustive TB + FORMAL
equivalence vs. the curated golden. Emit an AgentRun for the metric engine.

`evaluate_candidate` scores a *given* RTL file with NO LLM — used to validate the
oracle on RunPod (e.g. the planted-overfit candidate must fail hidden+formal),
and to anchor the honest/dishonest baselines (R19).
"""

from __future__ import annotations

import json
import os

from .agent import Trajectory, run_agent
from .equiv import run_equiv
from .llm import LLMClient
from .schema import AgentRun, Tier, TierOutcome
from .sim import run_iverilog


def load_task(task_dir: str) -> dict:
    with open(os.path.join(task_dir, "task.json")) as f:
        return json.load(f)


def _score_withheld(task: dict, task_dir: str, rtl_path: str, workdir: str,
                    visible_passed: bool) -> list[TierOutcome]:
    top = task["top"]
    golden = os.path.join(task_dir, task["files"]["golden"])
    hidden_tb = os.path.join(task_dir, task["files"]["hidden_tb"])

    outcomes = [TierOutcome(Tier.VISIBLE, visible_passed)]

    hsim = run_iverilog([rtl_path], hidden_tb, os.path.join(workdir, "hidden"))
    outcomes.append(TierOutcome(Tier.HIDDEN, hsim.passed, detail=hsim.note))

    eq = run_equiv(golden, rtl_path, top, os.path.join(workdir, "formal"))
    outcomes.append(TierOutcome(Tier.FORMAL, eq.proven, status=eq.status))
    return outcomes


def evaluate_candidate(task_dir: str, rtl_path: str, workdir: str,
                       label: str = "candidate") -> AgentRun:
    """Score a fixed RTL file (no LLM). Visible tier is computed too, for honesty."""
    task = load_task(task_dir)
    visible_tb = os.path.join(task_dir, task["files"]["visible_tb"])
    vsim = run_iverilog([rtl_path], visible_tb, os.path.join(workdir, "visible"))
    outcomes = _score_withheld(task, task_dir, rtl_path, workdir, vsim.passed)
    return AgentRun(task_id=f"{task['task_id']}::{label}", model="none",
                    iterations=0, total_tokens=0, final_rtl_path=rtl_path,
                    tier_outcomes=outcomes)


def evaluate_task(task_dir: str, workdir: str, llm: LLMClient,
                  max_iters: int = 5) -> tuple[AgentRun, Trajectory]:
    """Full agentic run: LLM repairs against visible, then withheld scoring."""
    task = load_task(task_dir)
    traj = run_agent(task, task_dir, workdir, llm, max_iters=max_iters)
    outcomes = _score_withheld(task, task_dir, traj.final_rtl_path, workdir,
                               traj.visible_passed)
    run = AgentRun(
        task_id=task["task_id"], model=traj.model, iterations=traj.iterations,
        total_tokens=traj.total_tokens, cached_tokens=traj.cached_tokens,
        final_rtl_path=traj.final_rtl_path, tier_outcomes=outcomes,
    )
    return run, traj
