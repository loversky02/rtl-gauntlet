"""Generate the paper figures (PDF) from the real result numbers. matplotlib Agg.

  python3 scripts/make_figures.py   →  paper/figures/{progression,models,cost}.pdf
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = "paper/figures"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 11, "figure.dpi": 150, "savefig.bbox": "tight"})


def fig_progression():
    stages = ["naïve", "+reset\n+don't-care", "+BMC", "+SV", "+memory"]
    false_cex = [9, 3, 1, 1, 1]
    inconclusive = [50, 50, 50, 14, 6]
    honest = [88, 91, 94, 128, 135]            # honest + bmc_equiv
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.plot(stages, false_cex, "o-", color="#c0392b", label="false CEX")
    ax.plot(stages, inconclusive, "s-", color="#e67e22", label="inconclusive")
    ax.plot(stages, honest, "^-", color="#27ae60", label="honest (incl. bmc)")
    for x, y in enumerate(false_cex):
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=9)
    for x, y in enumerate(inconclusive):
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=9)
    ax.set_ylabel("# of 156 tasks (Opus 4.8)")
    ax.set_title("Oracle hardening: artifacts fall, honest pass rises")
    ax.legend(loc="center right")
    ax.grid(True, alpha=0.3)
    fig.savefig(f"{OUT}/progression.pdf")
    plt.close(fig)


def fig_models():
    cats = ["honest", "bmc", "dontcare", "RHG_cex", "inconcl", "fail", "no-cand"]
    opus = [129, 6, 5, 1, 6, 9, 0]
    haiku = [104, 3, 0, 1, 7, 30, 11]
    x = range(len(cats))
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    w = 0.4
    ax.bar([i - w / 2 for i in x], opus, w, label="Opus 4.8", color="#2980b9")
    ax.bar([i + w / 2 for i in x], haiku, w, label="Haiku 4.5", color="#8e44ad")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, rotation=20, ha="right")
    ax.set_ylabel("# of 156 tasks")
    ax.set_title("Weakness ≠ hacking: Haiku fails 3×, hacks no more (RHG_cex=1, verified artifact)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.savefig(f"{OUT}/models.pdf")
    plt.close(fig)


def fig_cost():
    models = ["Opus 4.8", "Haiku 4.5"]
    saved = [11.6, 23.4]
    payoff = [35, 14]
    x = range(len(models))
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    w = 0.35
    ax.bar([i - w / 2 for i in x], saved, w, label="tokens saved (early-stop @1) %", color="#16a085")
    ax.bar([i + w / 2 for i in x], payoff, w, label="repair-tail payoff %", color="#d35400")
    ax.set_xticks(list(x))
    ax.set_xticklabels(models)
    ax.set_ylabel("%")
    ax.set_title("Cost: the repair tail is mostly wasted (~5% honesty lost)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.savefig(f"{OUT}/cost.pdf")
    plt.close(fig)


if __name__ == "__main__":
    fig_progression()
    fig_models()
    fig_cost()
    print("wrote", os.listdir(OUT))
