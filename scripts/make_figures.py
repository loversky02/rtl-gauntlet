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
    stages = ["naïve", "+reset\n+don't-care", "+BMC", "+SV", "+memory", "+reset\n-BMC", "+careset"]
    false_cex = [9, 3, 1, 1, 1, 1, 1]          # Opus residual = circuit8 (mixed-edge, hand-verified)
    inconclusive = [50, 50, 50, 14, 6, 0, 0]
    honest = [88, 91, 94, 128, 135, 140, 144]  # honest + bmc_equiv + careset_equiv (Opus 129+11+4)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.plot(stages, false_cex, "o-", color="#c0392b", label="false CEX")
    ax.plot(stages, inconclusive, "s-", color="#e67e22", label="inconclusive")
    ax.plot(stages, honest, "^-", color="#27ae60", label="honest (incl. bmc)")
    for x, y in enumerate(false_cex):        # below the red line
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, -15),
                    ha="center", fontsize=9, color="#c0392b")
    for x, y in enumerate(inconclusive):     # above the orange line
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=9, color="#e67e22")
    ax.set_ylim(-12, 158)
    ax.set_ylabel("# of 156 tasks (Opus 4.8)")
    ax.set_title("Oracle hardening: artifacts fall, honest pass rises")
    ax.legend(loc="center right")
    ax.grid(True, alpha=0.3)
    fig.savefig(f"{OUT}/progression.pdf")
    plt.close(fig)


def fig_models():
    cats = ["honest", "bmc", "careset", "dontcare", "RHG_cex", "inconcl", "fail", "no-cand"]
    opus = [129, 11, 4, 2, 1, 0, 9, 0]         # resweep_opus_careset
    gpt = [126, 12, 6, 3, 1, 2, 6, 0]          # resweep_gpt_careset
    gemini = [123, 11, 6, 1, 0, 1, 14, 0]      # resweep_gemini_careset
    deepseek = [113, 5, 2, 0, 0, 0, 36, 0]     # resweep_deepseek_careset
    haiku = [109, 4, 1, 1, 0, 0, 30, 11]       # resweep_haiku_careset
    x = range(len(cats))
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    w = 0.16
    ax.bar([i - 2 * w for i in x], opus, w, label="Opus 4.8", color="#2980b9")
    ax.bar([i - 1 * w for i in x], gpt, w, label="GPT-5.5", color="#e67e22")
    ax.bar(list(x), gemini, w, label="Gemini 2.5", color="#c0392b")
    ax.bar([i + 1 * w for i in x], deepseek, w, label="DeepSeek", color="#27ae60")
    ax.bar([i + 2 * w for i in x], haiku, w, label="Haiku 4.5", color="#8e44ad")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, rotation=20, ha="right")
    ax.set_ylabel("# of 156 tasks")
    ax.set_title("Weakness ≠ hacking (5 models): flagged RHG_cex 9→2 (careset-proven; circuit8 residual)")
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.grid(True, axis="y", alpha=0.3)
    fig.savefig(f"{OUT}/models.pdf")
    plt.close(fig)


def fig_cost():
    models = ["Opus", "GPT-5.5", "Haiku", "Gemini"]   # 4 models with per-iter token logs
    saved = [11.6, 17.2, 23.4, 24.2]   # early-stop@1 tokens saved %  (analyze_cost.py)
    payoff = [47, 59, 14, 48]          # repair-tail payoff %
    x = range(len(models))
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    w = 0.38
    ax.bar([i - w / 2 for i in x], saved, w, label="tokens saved (early-stop @1) %", color="#16a085")
    ax.bar([i + w / 2 for i in x], payoff, w, label="repair-tail payoff %", color="#d35400")
    ax.set_xticks(list(x))
    ax.set_xticklabels(models)
    ax.set_ylabel("%")
    ax.set_ylim(0, 58)
    ax.set_title("Cost: the repair tail is mostly wasted (~5% honesty lost)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)
    fig.savefig(f"{OUT}/cost.pdf")
    plt.close(fig)


if __name__ == "__main__":
    fig_progression()
    fig_models()
    fig_cost()
    print("wrote", os.listdir(OUT))
