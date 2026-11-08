"""Render shareable figures directly from a completed report; no invented data.

Requires matplotlib (optional presentation dependency, not needed by the engine).
Usage: python scripts/plot_results.py runs/<run>/report.json
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("report", type=Path)
parser.add_argument("--out", type=Path, default=Path("docs/assets"))
args = parser.parse_args()
r = json.loads(args.report.read_text())
args.out.mkdir(parents=True, exist_ok=True)
PAPER, INK, MUTED, GREEN, RED = "#f7f7f7", "#171717", "#838383", "#252525", "#555555"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#cfcfcf", "axes.labelcolor": INK,
                     "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER})


def finish(fig, name, note):
    fig.text(.07, .025, note, fontsize=8, color=MUTED)
    fig.savefig(args.out / f"{name}.png", dpi=180, bbox_inches="tight")
    fig.savefig(args.out / f"{name}.svg", bbox_inches="tight")
    svg = args.out / f"{name}.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)


versions = r["versions"]
active = versions[0]
scores = []
for v in versions:
    if v["accepted"]: active = v
    scores.append(100 * active["validation"]["detected"] / active["validation"]["total"])

fig, ax = plt.subplots(figsize=(10.5, 5.3))
fig.subplots_adjust(left=.09, right=.94, top=.81, bottom=.17)
fig.suptitle("The evaluation gets better. Regressions don't ship.", x=.07, ha="left", fontsize=19, fontweight="bold")
ax.step(range(len(versions)), scores, where="post", color=GREEN, linewidth=3, marker="o", markersize=8, label="Active evaluation")
ax.fill_between(range(len(versions)), scores, step="post", color=GREEN, alpha=.08)
for i, (v, score) in enumerate(zip(versions, scores)):
    ax.annotate(f'{int(score) if score.is_integer() else score:g}%', (i, score), xytext=(0, 12), textcoords="offset points", ha="center", fontsize=11, color=GREEN)
    if not v["accepted"]:
        candidate = 100 * v["validation"]["detected"] / v["validation"]["total"]
        ax.plot([i, i], [candidate, score], color=RED, linestyle="--", alpha=.6)
        ax.scatter([i], [candidate], color=RED, s=60, marker="x", zorder=4)
        ax.annotate("Rejected proposal", (i, candidate), xytext=(-12, -25), textcoords="offset points", ha="right", color=RED, fontsize=10)
ax.set_ylim(-5, 120); ax.set_yticks([0,25,50,75,100], ["0%","25%","50%","75%","100%"])
ax.set_xticks(range(len(versions)), [f"v{v['version']}" for v in versions]); ax.set_ylabel("Validation defects detected")
ax.grid(axis="y", alpha=.15); ax.set_axisbelow(True)
finish(fig,"self-improvement",f"{r['manifest']['mode']} · {r['validation_after']['total']} seeded validation variants · repeated validation guides promotion; final audit is separate.")

fig, axes = plt.subplots(1,2,figsize=(10.5,5.2),gridspec_kw={"width_ratios":[1.5,1]})
fig.subplots_adjust(left=.09,right=.95,top=.79,bottom=.2,wspace=.45)
fig.suptitle("The final audit: different code, frozen evaluation.",x=.07,ha="left",fontsize=19,fontweight="bold")
before,after=r["audit_before"],r["audit_after"]
values=[before["detected"],after["detected"]]
bars=axes[0].bar([0,1],values,color=["#bebebe",GREEN],width=.53)
axes[0].set_xticks([0,1],["Original suite",f"Promoted v{r['active_version']}"])
axes[0].set_ylim(0,after["total"]+1.5);axes[0].set_ylabel("Audit defects detected");axes[0].set_yticks(range(0,after["total"]+1,2))
for b,v in zip(bars,values): axes[0].text(b.get_x()+b.get_width()/2,v+.25,f"{v}/{after['total']}",ha="center",fontsize=17,fontweight="bold")
axes[1].axis("off")
axes[1].text(.05,.8,f"{after['false_rejections']}/{after['controls']}",fontsize=54,color=GREEN,transform=axes[1].transAxes)
axes[1].text(.05,.6,"Correct controls rejected",fontsize=12,transform=axes[1].transAxes)
axes[1].text(.05,.32,f"{after['total']-after['detected']} defect(s) still missed.\nEvery audit result is published.",fontsize=11,color=MUTED,linespacing=1.8,transform=axes[1].transAxes)
finish(fig,"final-audit","Small synthetic benchmark. Held-out implementations share defect families with discovery; this is not a real-world accuracy estimate.")

rows=[row for row in r["validation_after"]["rows"] if not row["correct"]]
matrix=np.array([[int(next(vr for vr in v["validation"]["rows"] if vr["id"]==row["id"])["detected"]) for v in versions] for row in rows])
fig,ax=plt.subplots(figsize=(13,max(5.8,len(rows)*.36+2)));fig.subplots_adjust(left=.46,right=.96,top=.91,bottom=.08)
fig.suptitle("Which blind spots disappear?",x=.07,ha="left",fontsize=20,fontweight="bold")
ax.imshow(matrix,cmap=ListedColormap(["#e6e6e6",GREEN]),vmin=0,vmax=1,aspect="auto")
ax.set_xticks(range(len(versions)),[f"v{v['version']}"+ (" · rejected" if not v["accepted"] else "") for v in versions],fontsize=9)
ax.set_yticks(range(len(rows)),[row["title"] for row in rows],fontsize=9)
for i in range(len(rows)):
    for j in range(len(versions)):ax.text(j,i,"caught" if matrix[i,j] else "missed",ha="center",va="center",fontsize=9,color="white" if matrix[i,j] else MUTED)
ax.tick_params(length=0);ax.spines[:].set_visible(False)
finish(fig,"coverage-matrix","Validation variants × proposed suites. Rejected proposals remain visible; they never replace the active suite.")

fig,ax=plt.subplots(figsize=(10.5,5.2));fig.subplots_adjust(left=.1,right=.94,top=.8,bottom=.19)
fig.suptitle("Detection gains have an execution cost.",x=.07,ha="left",fontsize=20,fontweight="bold")
for v in versions:
    val=v["validation"];x=len(v["suite"]);y=100*val["detected"]/val["total"]
    ax.scatter(x,y,s=150,color=GREEN if v["accepted"] else RED,marker="o" if v["accepted"] else "x",zorder=3)
    ax.annotate(f"v{v['version']} · {val['seconds']:.2f}s",(x,y),xytext=(10,10 if v["accepted"] else -22),textcoords="offset points",fontsize=10)
ax.set_xlabel("Input scenarios in the proposed suite");ax.set_ylabel("Validation detection (%)");ax.set_ylim(-8,120);ax.grid(alpha=.15)
finish(fig,"cost-vs-detection","Times sum per-candidate wall durations, not CPU time. Proposal generation and API latency are reported separately in the JSON evidence.")

if r["provider_calls"]:
    calls=r["provider_calls"]
    fig,ax=plt.subplots(figsize=(11,5.3));fig.subplots_adjust(left=.1,right=.94,top=.8,bottom=.3)
    fig.suptitle("What the live model calls actually consumed.",x=.07,ha="left",fontsize=19,fontweight="bold")
    counts=[c["usage"].get("input_tokens",c["usage"].get("prompt_tokens",0)) for c in calls]
    ax.bar(range(len(calls)),counts,color=[GREEN if c["provider"]=="subquadratic" else "#a9a9a9" for c in calls])
    ax.set_xticks(range(len(calls)),[c["purpose"].replace("-","\n") for c in calls],fontsize=8)
    ax.set_ylabel("Reported input tokens")
    finish(fig,"provider-usage","Usage comes from provider API responses. These are token counts, not a dollar-cost estimate.")

# A compact README figure: connecting lines join measured checkpoints only.
active = versions[0]
counts, scenarios = [], []
for v in versions:
    if v["accepted"]:
        active = v
    counts.append(active["validation"]["detected"])
    scenarios.append(len(active["suite"]))
x = list(range(len(versions)))
fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
fig.subplots_adjust(left=.08, right=.95, top=.73, bottom=.25, wspace=.31)
fig.text(.07, .93, "CrossExam gets better at finding broken code.", fontsize=22, weight="bold", color=INK)
fig.text(.07, .86, f"One recorded {r['manifest']['mode'].removeprefix('live ')} run. Each dot is a frozen evaluation version.", fontsize=11, color=MUTED)
for ax, values, title, ylabel, ceiling in zip(axes, [counts, scenarios],
        ["Faulty implementations caught", "Input scenarios in the active suite"],
        [f"Validation detections / {r['validation_after']['total']}", "Scenario count"],
        [r["validation_after"]["total"] + .6, max(scenarios) * 1.2]):
    ax.plot(x, values, color=INK, linewidth=2.7, marker="o", markersize=7, zorder=3)
    ax.fill_between(x, values, color=INK, alpha=.055)
    for i, value in enumerate(values):
        ax.annotate(str(value), (i, value), xytext=(0, 11), textcoords="offset points", ha="center", weight="bold", fontsize=12)
    ax.set_title(title, loc="left", fontsize=12, pad=20)
    ax.set_xticks(x, [f"v{v['version']}" for v in versions])
    ax.set_ylim(0, ceiling)
    ax.set_xlim(-.25, len(x)-.75)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=.14)
    ax.set_axisbelow(True)
axes[0].set_yticks(range(0, r["validation_after"]["total"] + 1, 2))
fig.text(.07, .115, f"FINAL AUDIT   {before['detected']}/{before['total']} → {after['detected']}/{after['total']} caught     ·     {after['false_rejections']}/{after['controls']} correct controls rejected", fontsize=12, weight="bold")
finish(fig, "improvement-curve", "Public synthetic benchmark. Lines connect measured checkpoints; final audit is measured only before and after learning.")

print(f"Rendered measured figures to {args.out}")
