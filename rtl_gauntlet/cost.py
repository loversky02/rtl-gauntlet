"""C2 cost axis — early-stop policy + cost/honesty trade-off analysis.

HORIZON's open problem is cheap convergence: a few categories absorb most of the budget.
Here we model an early-stop policy (cap the repair loop at k iterations) and quantify the
cost saved vs. the honest passes lost, from sweep logs that record (iters, tokens, category).
Stdlib only.
"""

from __future__ import annotations

from collections.abc import Sequence

HONEST_CATS = {"honest", "bmc_equiv"}


def _per_iter_tokens(row: dict) -> float:
    it = max(int(row.get("iters", 1) or 1), 1)
    return float(row.get("tokens", 0) or 0) / it


def early_stop_tradeoff(rows: Sequence[dict], k: int) -> dict:
    """Simulate stopping every repair loop at <= k iterations.

    A task that used more than k iterations would, under the cap, not get its later
    iterations: it loses whatever it gained there. Since a task only runs iteration i+1
    because iteration i did NOT pass the visible test, capping at k turns every
    >k-iteration task into a visible-fail — so any honest outcome among them is lost.
    Tokens saved = the >k-iteration portion (approx. per-iter * (iters-k)).
    """
    total_tokens = sum(float(r.get("tokens", 0) or 0) for r in rows)
    saved = 0.0
    lost_honest = 0
    capped = 0
    for r in rows:
        it = int(r.get("iters", 1) or 1)
        if it > k:
            capped += 1
            saved += _per_iter_tokens(r) * (it - k)
            if r.get("category") in HONEST_CATS:
                lost_honest += 1
    honest_total = sum(1 for r in rows if r.get("category") in HONEST_CATS)
    return {
        "k": k,
        "tasks_capped": capped,
        "tokens_saved": round(saved),
        "tokens_saved_pct": round(100 * saved / total_tokens, 1) if total_tokens else 0.0,
        "honest_lost": lost_honest,
        "honest_kept": honest_total - lost_honest,
        "honest_total": honest_total,
    }


def iteration_value(rows: Sequence[dict]) -> dict:
    """Of the tasks that needed >1 iteration, how often did the extra work pay off
    (end honest)? Low payoff ⇒ the repair tail is mostly wasted budget."""
    tail = [r for r in rows if int(r.get("iters", 1) or 1) > 1]
    paid = sum(1 for r in tail if r.get("category") in HONEST_CATS)
    return {
        "multi_iter_tasks": len(tail),
        "ended_honest": paid,
        "payoff_rate": round(paid / len(tail), 3) if tail else float("nan"),
    }
