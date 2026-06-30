"""RTL Gauntlet — honesty / cost / latency metrics for agentic hardware design."""

from .schema import Tier, TierOutcome, TaskSpec, AgentRun
from .metrics import (
    visible_pass_rate,
    hidden_pass_rate,
    honest_pass_rate,
    reward_hacking_gap,
    tier_gap,
    token_stats,
)

__all__ = [
    "Tier",
    "TierOutcome",
    "TaskSpec",
    "AgentRun",
    "visible_pass_rate",
    "hidden_pass_rate",
    "honest_pass_rate",
    "reward_hacking_gap",
    "tier_gap",
    "token_stats",
]

__version__ = "0.0.1"
