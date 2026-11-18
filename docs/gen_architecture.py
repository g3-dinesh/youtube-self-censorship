"""Draws the architecture block diagram (docs/architecture.png).
Run once: python docs/gen_architecture.py
"""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
BLUE, ORANGE, GREEN, VERM, GREY, INK = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#eef1f4", "#1a1a1a"

fig, ax = plt.subplots(figsize=(13, 8.5)); ax.axis("off")
ax.set_xlim(0, 13); ax.set_ylim(0, 9)


def box(x, y, w, h, text, fc, fs=8.5, tc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.1",
                                fc=fc, ec="none"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, weight="bold", wrap=True)


def store(x, y, w, h, text):
    box(x, y, w, h, text, GREY, fs=7.5, tc=INK)


def arrow(x1, y1, x2, y2, col="#888"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=12, color=col, lw=1.3))


def band(x, y, w, h, label, col):
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=col, ec="none", alpha=0.08))
    ax.text(x + 0.12, y + h - 0.22, label, fontsize=9.5, color=col, weight="bold")


# stage bands
band(0.2, 6.7, 12.6, 2.0, "STAGE 1  ·  COLLECT (local machine)", BLUE)
band(0.2, 4.6, 12.6, 1.9, "STAGE 2  ·  SIGNALS", ORANGE)
band(0.2, 2.5, 12.6, 1.9, "STAGE 3  ·  JUDGES (Ollama GPU server)", VERM)
band(0.2, 0.3, 12.6, 1.9, "STAGE 4  ·  ANALYSIS + FIGURES", GREEN)

# stage 1
store(0.5, 7.7, 2.1, 0.7, "channels.csv\n+ start year")
box(3.0, 7.6, 2.7, 0.9, "01 collect_channel_\ntranscripts.py", BLUE)
store(6.1, 7.7, 2.0, 0.7, "transcripts.jsonl\nvideo_index.csv")
box(3.0, 6.8, 2.7, 0.7, "03 fetch_single_video.py\n(one video id)", BLUE, fs=7.5)
store(6.1, 6.85, 2.0, 0.6, "single_<id>.json")
arrow(2.6, 8.05, 3.0, 8.05); arrow(5.7, 8.05, 6.1, 8.05)

# stage 2
box(0.5, 4.75, 2.6, 0.9, "02 scrape_video_\nmetadata.py", ORANGE)
store(3.3, 4.85, 1.7, 0.7, "video_\nmetadata.csv")
box(5.2, 4.75, 2.4, 0.9, "04 ad_checker.py", ORANGE)
store(7.8, 4.85, 1.7, 0.7, "ad_\nobservations.csv")
box(9.7, 4.75, 2.8, 0.9, "05 self_censorship_\nscan.py", ORANGE)
arrow(7.1, 7.6, 1.8, 5.65)     # video_index -> metadata
arrow(7.1, 7.6, 6.4, 5.65)     # video_index -> ad_checker
arrow(7.1, 7.6, 11.0, 5.65)    # transcripts -> self-censorship

# stage 3
box(1.6, 2.65, 3.0, 0.95, "06 system_a_judge.py\n(official policy)", VERM)
store(0.4, 2.7, 1.0, 0.85, "policy_\ncorpus")
box(5.4, 2.65, 3.0, 0.95, "07 system_b_judge.py\n(creator folk belief)", VERM)
store(8.6, 2.7, 1.0, 0.85, "folk_\nrules")
store(10.0, 2.7, 2.4, 0.9, "systemA/B_\nverdicts.csv")
arrow(1.4, 3.1, 1.6, 3.1); arrow(8.6, 3.1, 8.4, 3.1)
arrow(4.6, 3.0, 10.0, 3.2); arrow(8.4, 2.9, 10.0, 3.0)

# stage 4
box(0.5, 0.5, 2.7, 0.95, "08 policy_\navoidance.py", GREEN)
box(3.6, 0.5, 2.7, 0.95, "09 timeline_\nanalysis.py", GREEN)
box(6.7, 0.5, 2.7, 0.95, "10 counterfactual_\nexperiment.py", GREEN)
store(9.9, 0.55, 2.5, 0.85, "CSVs + PNG\nfigures")
arrow(11.1, 2.65, 1.9, 1.45)    # verdicts -> policy_avoidance
arrow(8.0, 4.75, 5.0, 1.45)     # signals -> timeline
arrow(3.2, 0.97, 3.6, 0.97); arrow(6.3, 0.97, 6.7, 0.97); arrow(9.4, 0.97, 9.9, 0.97)

# shared util note
ax.text(6.5, 0.05, "common.py  —  shared masking detector, lexicon, Wilson CIs, dataset loader  |  "
        "backend: policy_rag · monetisation_judge · poc_* (RAG + Ollama)",
        ha="center", fontsize=7.5, color="#555", style="italic")

ax.set_title("YouTube Self-Censorship — pipeline architecture", fontsize=14, weight="bold", y=1.0)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "architecture.png"), dpi=140, bbox_inches="tight")
print("-> docs/architecture.png")
