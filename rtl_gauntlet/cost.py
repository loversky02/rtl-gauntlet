"""C2 cost axis — early-stop policy + cost/honesty trade-off analysis.

HORIZON's open problem is cheap convergence: a few categories absorb most of the budget.
Here we model an early-stop policy (cap the repair loop at k iterations) and quantify the
cost saved vs. the honest passes lost, from sweep logs that record (iters, tokens, category).
Stdlib only.
"""

from __future__ import annotations

from collections.abc import Sequence

HONEST_CATS = {"honest", "bmc_equiv", "careset_equiv"}


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


def prospective_early_stop(train_rows: Sequence[dict], test_rows: Sequence[dict],
                           ks: Sequence[int] = (1, 2, 3), max_honest_loss_pct: float = 5.0) -> dict:
    """PROSPECTIVE early-stop: choose the cap `k` on `train_rows` (the smallest k whose honesty
    loss stays within `max_honest_loss_pct`), then REPORT the realized trade-off on held-out
    `test_rows`. Unlike the post-hoc `early_stop_tradeoff`, the threshold never sees the test
    outcomes it is scored on — answering the reviewer's ``don't tune and evaluate on the same data.''"""
    chosen = max(ks)
    for k in sorted(ks):
        t = early_stop_tradeoff(train_rows, k)
        loss_pct = 100 * t["honest_lost"] / t["honest_total"] if t["honest_total"] else 0.0
        if loss_pct <= max_honest_loss_pct:
            chosen = k
            break
    realized = early_stop_tradeoff(test_rows, chosen)
    loss = (100 * realized["honest_lost"] / realized["honest_total"]) if realized["honest_total"] else 0.0
    return {
        "chosen_k": chosen,
        "test_tokens_saved_pct": realized["tokens_saved_pct"],
        "test_honest_lost": realized["honest_lost"],
        "test_honest_lost_pct": round(loss, 1),
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
