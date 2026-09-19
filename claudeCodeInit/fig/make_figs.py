#!/usr/bin/env python3
"""Figures for paper.pdf. Vector PDF out, Times-metric serif to match the LaTeX body."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"   # validated slots 1-3
INK, MUTED, GRID    = "#0b0b0b", "#52514e", "#dcdcd8"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "DejaVu Serif"],
    "font.size": 7.4,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.015,
})

def despine(ax, keep=("left","bottom")):
    for s in ("top","right","left","bottom"):
        ax.spines[s].set_visible(s in keep)

# ---------------------------------------------------------------- Figure 1
# Every measured effect on task success, against the measured noise floor.
rows = [
    ("Codex, selective ctx",            -5.9, "Khatri"),
    ("AGENTbench, LLM-written",         -2.0, "Gloaguen"),
    ("Codex, always-on ctx",            -1.9, "Khatri"),
    ("SWE-bench Lite, LLM-written",     -0.5, "Gloaguen"),
    ("Claude Code, always-on ctx",      +2.3, "Khatri"),
    ("Claude Code, selective ctx",      +2.3, "Khatri"),
    ("Docs stripped, LLM-written",      +2.7, "Gloaguen"),
    ("AGENTbench, developer-written",   +4.0, "Gloaguen"),
]
fig, ax = plt.subplots(figsize=(3.34, 2.42))
ax.axvspan(-9, 9, color=AQUA, alpha=0.13, lw=0, zorder=0)
ax.axvline(0, color=MUTED, lw=0.7, zorder=1)
ys = range(len(rows))
for y,(lab,val,src) in zip(ys, rows):
    c = BLUE if src == "Gloaguen" else ORANGE
    ax.plot([0,val],[y,y], color=c, lw=1.1, alpha=.55, zorder=2, solid_capstyle="round")
    ax.plot(val, y, "o", ms=5.2, color=c, mec="white", mew=.9, zorder=3)
    ax.annotate(f"{val:+.1f}", (val,y), textcoords="offset points",
                xytext=(9 if val>=0 else -9,0), ha="left" if val>=0 else "right",
                va="center", fontsize=6.4, color=INK)
ax.set_yticks(list(ys)); ax.set_yticklabels([r[0] for r in rows], fontsize=6.6)
ax.set_xlim(-12.5, 12.5); ax.set_ylim(-0.7, len(rows)+0.05)
ax.set_xlabel("Change in task success (percentage points)", fontsize=7)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_: f"{v:+.0f}"))
ax.grid(axis="x", color=GRID, lw=0.5, zorder=0); ax.set_axisbelow(True)
despine(ax)
ax.annotate("run-to-run noise floor (±9 pp)", xy=(0, len(rows)-0.62),
            ha="center", fontsize=6.3, color="#137a56", style="italic")
h = [plt.Line2D([],[],marker="o",ls="",color=BLUE,ms=5,label="Gloaguen et al."),
     plt.Line2D([],[],marker="o",ls="",color=ORANGE,ms=5,label="Khatri")]
ax.legend(handles=h, fontsize=6.2, frameon=False, loc="lower right",
          handletextpad=.3, borderaxespad=.2)
fig.savefig("fig/fig1_forest.pdf"); plt.close(fig)

# ---------------------------------------------------------------- Figure 2
# Cost is the one effect that is not in the noise.
models = ["Sonnet-4.5", "GPT-5.2", "GPT-5.1-mini", "Qwen3-30B"]
none   = [1.15, 0.38, 0.18, 0.13]
llm    = [1.33, 0.57, 0.20, 0.15]
human  = [1.30, 0.54, 0.19, 0.15]
inc_l  = [(a-b)/b*100 for a,b in zip(llm,none)]
inc_h  = [(a-b)/b*100 for a,b in zip(human,none)]
fig, ax = plt.subplots(figsize=(3.34, 1.98))
w = 0.36; xs = range(len(models))
b1 = ax.bar([x-w/2-0.012 for x in xs], inc_l, w, color=BLUE,   label="LLM-written", zorder=3)
b2 = ax.bar([x+w/2+0.012 for x in xs], inc_h, w, color=ORANGE, label="Developer-written", zorder=3)
for bars in (b1,b2):
    for r in bars:
        ax.annotate(f"+{r.get_height():.0f}%", (r.get_x()+r.get_width()/2, r.get_height()),
                    textcoords="offset points", xytext=(0,2.0), ha="center",
                    fontsize=6.1, color=INK)
ax.axhline(0, color=MUTED, lw=0.7)
ax.set_xticks(list(xs)); ax.set_xticklabels(models, fontsize=6.8)
ax.set_ylabel("Increase in cost per task", fontsize=7)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: f"+{v:.0f}%"))
ax.set_ylim(0, max(inc_l)*1.26)
ax.grid(axis="y", color=GRID, lw=0.5, zorder=0); ax.set_axisbelow(True)
despine(ax)
ax.legend(fontsize=6.3, frameon=False, ncol=2, loc="upper center",
          bbox_to_anchor=(0.5,1.16), handlelength=1.1, columnspacing=1.2)
fig.savefig("fig/fig2_cost.pdf"); plt.close(fig)

# ---------------------------------------------------------------- Figure 3
# What authors put in these files, versus what the evidence supports.
cats = ["Test procedures", "Implementation detail", "Architecture overview",
        "Security", "Performance"]
vals = [75.9, 70.8, 68.1, 14.8, 14.5]
hi   = [False, False, True, False, False]
fig, ax = plt.subplots(figsize=(3.34, 1.72))
ys = range(len(cats))[::-1]
for y,(c,v,flag) in zip(ys, zip(cats,vals,hi)):
    ax.barh(y, v, height=.62, color=ORANGE if flag else BLUE, zorder=3)
    ax.annotate(f"{v:.1f}%", (v,y), textcoords="offset points", xytext=(4,0),
                va="center", fontsize=6.3, color=INK)
ax.set_yticks(list(ys)); ax.set_yticklabels(cats, fontsize=6.7)
ax.set_xlim(0, 100); ax.set_xlabel("Share of context files containing the category", fontsize=7)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_: f"{v:.0f}%"))
ax.grid(axis="x", color=GRID, lw=0.5, zorder=0); ax.set_axisbelow(True)
despine(ax)
ax.annotate("measured not to help", xy=(68.1, 2), xytext=(52, 0.62),
            fontsize=6.2, color=ORANGE, ha="left", va="center",
            arrowprops=dict(arrowstyle="->", color=ORANGE, lw=.7, shrinkB=3,
                            connectionstyle="angle3,angleA=10,angleB=-70"))
fig.savefig("fig/fig3_content.pdf"); plt.close(fig)
print("wrote fig1_forest.pdf fig2_cost.pdf fig3_content.pdf")
