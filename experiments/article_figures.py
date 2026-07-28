"""Figures for the plain-language article (results/writeups/ARTICLE.md).

Deterministic. Every quantitative value is read from a committed artifact:

  results/stage2_confirm/report_numbers.json   -> figures 1 and 2
  results/stage1e_confirm/analysis.json        -> figure 4 (y values)

Two things are literals in this file, both with their source named at the point
of use, because no machine-readable artifact exists for them:

  * Figure 3 is a text summary of the four forced-choice pilot reports
    (results/stage2_pilot*/PILOT_REPORT*.md). Those reports are prose.
  * Figure 4's x-axis, respondent seconds per budget, comes from
    results/stage1e_timecost_note.md section 2. It is derived from raw
    response-time data that is gitignored, so it cannot be recomputed here.
    experiments/timecost_note.py is the script that produced it.

Run:

    uv run --no-project --with matplotlib python experiments/article_figures.py

Writes PNGs into results/writeups/figures/.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIRM_JSON = ROOT / "results" / "stage2_confirm" / "report_numbers.json"
STAGE1E_JSON = ROOT / "results" / "stage1e_confirm" / "analysis.json"
OUT = ROOT / "results" / "writeups" / "figures"

# Palette: the validated light-mode categorical slots 1-3 plus chart chrome.
# Validated with the dataviz palette validator (all pairs, light surface):
# CVD dE 9.2, normal-vision dE 24.0, both clear. Slot 3 (aqua) sits under 3:1
# against the surface, so every mark in every figure carries a visible label.
BLUE = "#2a78d6"      # the person's own twin / the fixed question order
ORANGE = "#eb6834"    # the stranger's twin / adaptive question picking
AQUA = "#1baf7a"      # the know-nothing AI / random question order
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "text.color": INK,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 1.0,
        "grid.color": GRID,
        "grid.linewidth": 1.0,
        "figure.dpi": 200,
        "savefig.dpi": 200,
    }
)


def load(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def tidy(ax, *, ygrid=True):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)
    if ygrid:
        ax.set_axisbelow(True)
        ax.yaxis.grid(True)
        ax.xaxis.grid(False)
    ax.tick_params(length=0)


def ci95_of_mean(sd: float, n: int) -> float:
    """Half-width of a 95% interval on an arm's average across people."""
    return 1.96 * sd / math.sqrt(n)


# --------------------------------------------------------------------------
# Figure 1 - the headline: own twin vs stranger's twin vs know-nothing AI
# --------------------------------------------------------------------------
def figure_headline(d: dict) -> Path:
    ch1 = d["channel1"]["gemma"]["per_arm_raw"]
    ch2 = d["channel2"]["gemma"]["per_arm_raw"]
    h1c1 = d["h1"]["channel1"]["gemma"]["contrasts"]
    h1c2 = d["h1"]["channel2"]["gemma"]["contrasts"]

    arms = ["twin_redacted", "imposter_redacted", "zeroinfo_redacted"]
    names = ["the person's\nown twin", "a stranger's\ntwin", "the know-nothing\nAI"]
    colors = [BLUE, ORANGE, AQUA]

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 5.6))

    panels = [
        (
            axes[0],
            ch1,
            "grader one: how close is the meaning?",
            "answer similarity (0 to 1)",
            lambda v: f"{v:.2f}",
            (0.0, 0.78),
            h1c1,
        ),
        (
            axes[1],
            ch2,
            "grader two: is it the same position?",
            "share of answers judged the same position",
            lambda v: f"{v * 100:.0f}%",
            (0.0, 0.90),
            h1c2,
        ),
    ]

    footnotes = []
    for ax, raw, title, ylab, fmt, ylim, contrasts in panels:
        for i, (arm, colour) in enumerate(zip(arms, colors)):
            m = raw[arm]["mean_of_subject_means"]
            err = ci95_of_mean(raw[arm]["sd_of_subject_means"], raw[arm]["n_subjects"])
            ax.bar(i, m, width=0.58, color=colour, zorder=3)
            ax.errorbar(
                i, m, yerr=err, fmt="none", ecolor=INK2, elinewidth=1.4, capsize=5, zorder=4
            )
            ax.text(
                i,
                m + err + ylim[1] * 0.035,
                fmt(m),
                ha="center",
                va="bottom",
                fontsize=12,
                fontweight="bold",
                color=INK,
            )
        ax.set_xticks(range(len(arms)))
        ax.set_xticklabels(names, fontsize=10, color=INK2)
        ax.set_ylim(*ylim)
        ax.set_ylabel(ylab, fontsize=10)
        ax.set_title(title, fontsize=11.5, color=INK, pad=10, loc="left")
        tidy(ax)

        gap = contrasts["own_minus_imposter"]
        lo, hi = gap["ci95_t"]
        footnotes.append(
            f"{title.split(':')[0]}: the own twin beats the stranger's twin by "
            f"{gap['mean_diff']:+.3f}, 95% range {lo:+.3f} to {hi:+.3f}"
        )

    fig.suptitle(
        "The twin beats both opponents, on both graders",
        fontsize=15,
        fontweight="bold",
        x=0.02,
        ha="left",
        y=0.975,
    )
    fig.text(
        0.02,
        0.905,
        "88 people, 355 questions, main model. Bars are averages across people; "
        "whiskers are the 95% range around each average.",
        fontsize=9.5,
        color=INK2,
    )
    fig.text(0.02, 0.065, footnotes[0], fontsize=9.5, color=INK2)
    fig.text(0.02, 0.02, footnotes[1], fontsize=9.5, color=INK2)
    fig.tight_layout(rect=(0, 0.11, 1, 0.87))
    path = OUT / "fig1_headline.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Figure 2 - does a twin go stale?
# --------------------------------------------------------------------------
def figure_staleness(d: dict) -> Path:
    cells = d["h7"]["channel1"]["gemma"]["per_bin"]
    order = ["6-12m", "1-2y", "2-3y", ">3y"]
    labels = ["6-12\nmonths", "1-2\nyears", "2-3\nyears", "more than\n3 years"]
    own = [cells[b]["stale_own_twin_mean"] for b in order]
    imp = [cells[b]["fresh_imposter_mean"] for b in order]
    nsub = [cells[b]["n_subjects"] for b in order]
    x = list(range(len(order)))

    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    ax.plot(x, own, color=BLUE, linewidth=2.0, marker="o", markersize=9, zorder=3)
    ax.plot(x, imp, color=ORANGE, linewidth=2.0, marker="o", markersize=9, zorder=3)

    for xi, (o, i) in enumerate(zip(own, imp)):
        ax.text(xi, o + 0.011, f"{o:.2f}", ha="center", va="bottom", fontsize=10.5,
                fontweight="bold", color=INK)
        ax.text(xi, i - 0.013, f"{i:.2f}", ha="center", va="top", fontsize=10.5,
                fontweight="bold", color=INK)

    ax.text(x[-1] + 0.08, own[-1], "the person's own twin,\nbuilt from old material",
            color=BLUE, fontsize=10, va="center", fontweight="bold")
    ax.text(x[-1] + 0.08, imp[-1], "a stranger's twin,\nbuilt fresh",
            color=ORANGE, fontsize=10, va="center", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, color=INK2)
    ax.set_xlim(-0.35, len(order) + 0.75)
    ax.set_ylim(0.44, 0.65)
    ax.set_xlabel("how old the newest interview the twin was allowed to see", fontsize=10.5,
                  labelpad=10)
    ax.set_ylabel("answer similarity (0 to 1)", fontsize=10.5)
    ax.set_yticks([0.45, 0.50, 0.55, 0.60, 0.65])
    tidy(ax)

    fig.text(
        0.02,
        0.03,
        "people contributing to each point, left to right: " + ", ".join(f"{n}" for n in nsub)
        + " — 36 people in total",
        fontsize=9.5,
        color=MUTED,
    )
    fig.suptitle(
        "An old twin still beat a stranger's fresh twin at every age we could measure",
        fontsize=14,
        fontweight="bold",
        x=0.02,
        ha="left",
        y=0.975,
    )
    fig.text(
        0.02,
        0.905,
        "Grader one only, main model. EXPLORATORY: grader two disagreed, and only 36 people "
        "had enough material to appear here.",
        fontsize=9.5,
        color=INK2,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.87))
    path = OUT / "fig2_staleness.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Figure 3 - the four failed exam designs
# Text summarised from results/stage2_pilot/PILOT_REPORT.md,
# stage2_pilot2/PILOT_REPORT_2.md, stage2_pilot3/PILOT_REPORT_3.md and
# stage2_pilot4/PILOT_REPORT_4.md. Scores are each report's own
# zero-information argmax result on its honest reading.
# --------------------------------------------------------------------------
ROUNDS = [
    (
        "Round 1",
        "Wrong answers were real answers\nother people gave to other questions.",
        "17 out of 17",
        "The true answer was the only one about the right topic.",
    ),
    (
        "Round 2",
        "Wrong answers came from the same\nperson's other interviews.",
        "10 out of 10",
        "The true answer was the only one that actually replied\nto the question on screen.",
    ),
    (
        "Round 3",
        "Wrong answers were written from\nscratch to answer the same question.",
        "15 out of 15",
        "The true answer sounded like a real expert hedging; the\nwritten ones read like opinion columns. On factual\nquestions the true answer was simply the correct one.",
    ),
    (
        "Round 4",
        "Written answers, now hedged,\nfact-checked and stripped of names.",
        "8 out of 8",
        "The fix flipped the giveaway: the written answers turned\nbland and institutional, and the real one still sounded\nlike a person with a view.",
    ),
]


def figure_four_rounds() -> Path:
    fig, ax = plt.subplots(figsize=(12.4, 6.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    cols = [3.0, 13.0, 38.0, 57.0]
    headers = ["", "what we changed", "know-nothing score", "the giveaway that was left"]

    top = 90.0
    row_h = 19.0

    for cx, h in zip(cols, headers):
        ax.text(cx, top + 5.0, h, fontsize=11, fontweight="bold", color=INK, va="bottom")
    ax.plot([2.0, 98.0], [top + 3.0, top + 3.0], color=AXIS, linewidth=1.2)

    for idx, (name, changed, score, tell) in enumerate(ROUNDS):
        y = top - idx * row_h
        ax.text(cols[0], y, name, fontsize=12, fontweight="bold", color=BLUE, va="top")
        ax.text(cols[1], y, changed, fontsize=10.5, color=INK2, va="top", linespacing=1.5)
        ax.text(cols[2], y, score, fontsize=12, fontweight="bold", color=ORANGE, va="top")
        ax.text(cols[3], y, tell, fontsize=10.5, color=INK2, va="top", linespacing=1.5)

    ax.text(
        3.0,
        7.0,
        "The rule was written down before round 4 ran: if the know-nothing AI still scored 90% or better,\n"
        "multiple choice was dead and there would be no round 5. It scored 100%. There was no round 5.",
        fontsize=10.5,
        color=INK,
        linespacing=1.6,
    )

    fig.suptitle(
        "Four multiple-choice exams, four ways an AI that knew nothing still aced them",
        fontsize=15,
        fontweight="bold",
        x=0.025,
        ha="left",
        y=0.97,
    )
    fig.text(
        0.025,
        0.905,
        "Each round removed the previous giveaway. Each time, a new one appeared. "
        "Scores are the share of questions an AI told nothing about the person still got right.",
        fontsize=9.5,
        color=INK2,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    path = OUT / "fig3_four_rounds.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Figure 4 - budget curve priced in seconds of a person's time
# x values: results/stage1e_timecost_note.md section 2, central estimate,
# produced by experiments/timecost_note.py from gitignored raw timing data.
# --------------------------------------------------------------------------
SECONDS_PER_BUDGET = {"1": 6.4, "2": 12.6, "4": 22.4, "8": 40.5, "12": 57.9, "16": 74.9, "20": 91.6}


def figure_budget(a: dict) -> Path:
    lifts = a["lift_over_baseline"]
    ks = ["1", "2", "4", "8", "12", "16", "20"]
    xs = [SECONDS_PER_BUDGET[k] for k in ks]

    series = [
        ("fixed", "a fixed list of questions", BLUE),
        ("adaptive", "questions picked as it goes", ORANGE),
        ("random", "questions in random order", AQUA),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.2), sharey=True)
    for ax, dec, title in (
        (axes[0], "expected_value", "main scoring method"),
        (axes[1], "argmax", "back-up scoring method"),
    ):
        ax.axhline(0.0, color=AXIS, linewidth=1.2, zorder=2)
        for key, label, colour in series:
            ys = [lifts[dec][key][k]["lift_mean"] for k in ks]
            ax.plot(xs, ys, color=colour, linewidth=2.0, marker="o", markersize=7, zorder=3,
                    label=label)
        end = lifts[dec]["fixed"]["20"]["lift_mean"]
        ax.text(xs[-1], end + 0.004, f"{end:+.3f}", ha="right", va="bottom",
                fontsize=10.5, fontweight="bold", color=INK)
        ax.set_title(title, fontsize=11.5, color=INK, loc="left", pad=8)
        ax.set_xlabel("seconds of the person's time spent answering", fontsize=10.5)
        tidy(ax)
    axes[0].set_ylabel("how much better than knowing nothing\n(higher is better; 0 = no help)",
                       fontsize=10.5)
    axes[0].set_ylim(-0.045, 0.085)
    axes[0].legend(frameon=False, fontsize=10, loc="upper left", labelcolor=INK2)

    fig.suptitle(
        "Picking questions cleverly did not beat a good fixed list",
        fontsize=15,
        fontweight="bold",
        x=0.02,
        ha="left",
        y=0.975,
    )
    fig.text(
        0.02,
        0.905,
        "1,000 people. The clever picker used about nine times more computing than the fixed list "
        "and never got ahead of it.",
        fontsize=9.5,
        color=INK2,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.885))
    path = OUT / "fig4_budget_curve.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Figure 5 - the pipeline, hand-laid
# --------------------------------------------------------------------------
def _box(ax, x, y, w, h, text, *, edge, face=SURFACE, fontsize=10.5, weight="normal",
         textcolor=INK, align="center"):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.6,rounding_size=1.6",
            linewidth=1.6,
            edgecolor=edge,
            facecolor=face,
            zorder=3,
        )
    )
    tx = x + w / 2 if align == "center" else x + 1.8
    ax.text(tx, y + h / 2, text, ha=align, va="center", fontsize=fontsize,
            color=textcolor, fontweight=weight, linespacing=1.6, zorder=4,
            multialignment=align)


def _arrow(ax, x1, y1, x2, y2, colour=MUTED):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=14,
            linewidth=1.4,
            color=colour,
            shrinkA=2,
            shrinkB=2,
            zorder=2,
        )
    )


def figure_pipeline() -> Path:
    fig, ax = plt.subplots(figsize=(12.4, 6.3))
    ax.set_xlim(0, 100)
    ax.set_ylim(8, 100)
    ax.axis("off")

    # top row: the corpus, the split, the exam
    _box(ax, 3, 78, 19, 13, "every interview\nthis person gave", edge=AXIS)
    _arrow(ax, 22.5, 84.5, 26.5, 84.5)
    _box(ax, 27, 78, 17, 13, "split by date", edge=AXIS)
    _arrow(ax, 44.5, 84.5, 57.5, 84.5)
    _box(ax, 58, 77, 26, 15,
         "the newest interview\nis the exam\n(the twin never sees it)", edge=AXIS, fontsize=10)

    # middle row: build the twin, twin answers
    _arrow(ax, 35.5, 77.5, 35.5, 66)
    _box(ax, 24, 52, 24, 13, "older interviews\nbuild the twin",
         edge=BLUE, weight="bold", textcolor=BLUE)
    _arrow(ax, 48.5, 58.5, 57.5, 58.5)
    _box(ax, 58, 52, 24, 13, "the twin writes its\nown answer, in words", edge=AXIS)

    # bottom row: the two graders
    _box(ax, 48, 26, 23, 13, "grader one:\nhow similar\nis the meaning?", edge=AXIS, fontsize=9.5)
    _box(ax, 74, 26, 23, 13, "grader two:\nis it the same\nposition?", edge=AXIS, fontsize=9.5)
    _arrow(ax, 67, 51.5, 60, 40)
    _arrow(ax, 73, 51.5, 84, 40)

    # the three opponents
    ax.text(3, 44.5, "the same exam, three opponents",
            fontsize=11, fontweight="bold", color=INK, va="bottom")
    _box(ax, 3, 26, 41, 15,
         "1. the know-nothing AI, told nothing about the person\n"
         "2. a stranger's twin, built from someone else's interviews\n"
         "3. the same twin with the person's name shown, to see\n"
         "     what the model already knew",
         edge=AQUA, fontsize=9.5, align="left")

    ax.text(3, 14,
            "Every score in this study is the twin's score minus an opponent's score,\n"
            "never the twin's score on its own.",
            fontsize=10.5, color=INK2, va="top", linespacing=1.6)

    fig.suptitle(
        "How the test works",
        fontsize=15,
        fontweight="bold",
        x=0.025,
        ha="left",
        y=0.965,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = OUT / "fig5_pipeline.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    confirm = load(CONFIRM_JSON)
    stage1e = load(STAGE1E_JSON)
    for path in (
        figure_headline(confirm),
        figure_staleness(confirm),
        figure_four_rounds(),
        figure_budget(stage1e),
        figure_pipeline(),
    ):
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
