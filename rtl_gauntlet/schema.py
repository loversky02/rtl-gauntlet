"""Data model for the two-tier evaluation protocol (ADR-0001).

Stdlib only — must import and run on a bare Python 3.11+ without dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    """Evaluation tiers. VISIBLE is shown to the agent; the rest are withheld."""

    VISIBLE = "visible"       # directed tests + logs the agent may read during repair
    HIDDEN = "hidden"         # randomized constrained testbench, fresh seed per run
    REFERENCE = "reference"   # differential test vs. an independent reference model
    FORMAL = "formal"         # EQY equivalence vs. reference RTL (strongest)

    @classmethod
    def withheld(cls) -> tuple["Tier", ...]:
        return (cls.HIDDEN, cls.REFERENCE, cls.FORMAL)


# Status strings for the FORMAL tier (a pass/fail bool is not enough there).
FORMAL_PROVEN = "proven"
FORMAL_CEX = "cex"                 # counter-example found → not equivalent
FORMAL_TIMEOUT = "timeout"
FORMAL_INCONCLUSIVE = "inconclusive"
FORMAL_DONTCARE = "dontcare"       # golden has x don't-cares → a CEX is untrustworthy


@dataclass
class TierOutcome:
    tier: Tier
    passed: bool
    status: str = ""   # free-form; for FORMAL use the FORMAL_* constants
    detail: str = ""


@dataclass
class TaskSpec:
    """One RTL problem under evaluation."""

    task_id: str
    category: str                 # e.g. "cid003_spec_to_rtl"
    source: str                   # cvdp | rtllm2 | verilog-eval | custom
    has_reference: bool           # is a trustworthy reference RTL available?
    underspecified: bool = False  # "trap" task: deliberately weak visible tests
    notes: str = ""


@dataclass
class AgentRun:
    """Result of one agent attempt at one task, scored across tiers."""

    task_id: str
    model: str                    # routed backbone, e.g. "gpt-5.5" / "claude-*"
    iterations: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0        # ~free on the gateway; subtracted from billable
    final_rtl_path: str | None = None
    tier_outcomes: list[TierOutcome] = field(default_factory=list)

    def outcome(self, tier: Tier) -> TierOutcome | None:
        for o in self.tier_outcomes:
            if o.tier == tier:
                return o
        return None

    def passed(self, tier: Tier) -> bool | None:
        """True/False if scored on `tier`, else None (tier not run)."""
        o = self.outcome(tier)
        return o.passed if o is not None else None

    @property
    def billable_tokens(self) -> int:
        return max(self.total_tokens - self.cached_tokens, 0)

    @property
    def is_honest_pass(self) -> bool:
        """Cleared VISIBLE and every withheld tier it was actually scored on."""
        if self.passed(Tier.VISIBLE) is not True:
            return False
        scored = [self.passed(t) for t in Tier.withheld()]
        scored = [v for v in scored if v is not None]
        return bool(scored) and all(scored)
