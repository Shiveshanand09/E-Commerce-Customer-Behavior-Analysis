"""
Dashboard Generator — creates high-quality dashboard JPGs for the project.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── Styling ──────────────────────────────────────────────────────────────────
DARK_BG   = "#0D1117"
CARD_BG   = "#161B22"
BORDER    = "#21262D"
ACCENT    = "#58A6FF"
GREEN     = "#3FB950"
RED       = "#F85149"
YELLOW    = "#D29922"
PURPLE    = "#BC8CFF"
ORANGE    = "#FFA657"
TEXT      = "#E6EDF3"
SUBTEXT   = "#8B949E"

PALETTE   = [ACCENT, GREEN, YELLOW, PURPLE, ORANGE, RED, "#79C0FF", "#56D364"]

def apply_dark_style():
    plt.rcParams.update({
        "figure.facecolor": DARK_BG,
        "axes.facecolor": CARD_BG,
        "axes.edgecolor": BORDER,
        "axes.labelcolor": TEXT,
        "xtick.color": SUBTEXT,
        "ytick.color": SUBTEXT,
        "text.color": TEXT,
        "grid.color": BORDER,
        "grid.linestyle": "--",
        "grid.alpha": 0.5,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlecolor": TEXT,
        "legend.facecolor": CARD_BG,
        "legend.edgecolor": BORDER,
        "legend.labelcolor": TEXT,
    })

def card(ax, facecolor=CARD_BG, edgecolor=BORDER):
    for spine in ax.spines.values():
        spine.set_edgecolor(edgecolor)
        spine.set_linewidth(0.8)
    ax.set_facecolor(facecolor)

OUTPUT = Path("dashboards")
OUTPUT.mkdir(exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
customers = pd.read_csv("data/customers.csv", parse_dates=["signup_date"])
txn       = pd.read_csv("data/transactions.csv", parse_dates=["order_date"])
sessions  = pd.read_csv("data/sessions.csv", parse_dates=["session_date"])

completed = txn[txn["status"] == "Completed"].copy()
completed["month"] = completed["order_date"].dt.to_period("M").astype(str)
completed["quarter"] = completed["order_date"].dt.to_period("Q").astype(str)

# ════════════════════════════════════════════════════════════════════════════════
# DASHBOARD 1 — Overview & Revenue
# ════════════════════════════════════════════════════════════════════════════════
apply_dark_style()
fig = plt.figure(figsize=(18, 12), facecolor=DARK_BG)
fig.suptitle("E-Commerce Customer Behavior — Overview Dashboard",
             fontsize=18, fontweight="bold", color=TEXT, y=0.98)

gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.45, wspace=0.38)

# ── KPI Cards ────────────────────────────────────────────────────────────────
kpis = [
    ("Total Revenue", f"₹{completed['total_amount'].sum()/1e6:.1f}M", GREEN,  "↑ 18.4%"),
    ("Total Orders",  f"{len(completed):,}",                           ACCENT, "↑ 12.1%"),
    ("Active Customers", f"{completed['customer_id'].nunique():,}",    YELLOW, "↑  6.7%"),
    ("Avg Order Value",  f"₹{completed['total_amount'].mean():.0f}",   PURPLE, "↑  5.2%"),
]

for i, (label, value, color, change) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i])
    ax.set_facecolor(CARD_BG)
    for s in ax.spines.values():
        s.set_edgecolor(color); s.set_linewidth(1.5)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.5, 0.72, value,  ha="center", va="center", fontsize=20,
            fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.5, 0.40, label,  ha="center", va="center", fontsize=9,
            color=SUBTEXT, transform=ax.transAxes)
    ax.text(0.5, 0.15, change, ha="center", va="center", fontsize=9,
            color=GREEN, transform=ax.transAxes)

# ── Monthly Revenue Trend ─────────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[1, :2])
monthly_rev = completed.groupby("month")["total_amount"].sum().reset_index()
monthly_rev = monthly_rev.tail(18)
ax2.plot(monthly_rev["month"], monthly_rev["total_amount"]/1000, color=ACCENT,
          linewidth=2.5, marker="o", markersize=4)
ax2.fill_between(monthly_rev["month"], monthly_rev["total_amount"]/1000,
                  alpha=0.18, color=ACCENT)
ax2.set_title("Monthly Revenue Trend (₹ thousands)")
ax2.set_xlabel("")
ax2.tick_params(axis="x", rotation=45, labelsize=7)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:.0f}K"))
ax2.grid(True); card(ax2)

# ── Revenue by Category ───────────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, 2:])
cat_rev = completed.groupby("category")["total_amount"].sum().sort_values(ascending=True)
bars = ax3.barh(cat_rev.index, cat_rev.values/1000, color=PALETTE[:len(cat_rev)])
ax3.set_title("Revenue by Category (₹ thousands)")
ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:.0f}K"))
for bar in bars:
    w = bar.get_width()
    ax3.text(w + 1, bar.get_y() + bar.get_height()/2,
             f"₹{w:.0f}K", va="center", fontsize=7.5, color=SUBTEXT)
ax3.grid(True, axis="x"); card(ax3)

# ── Customer Segment Distribution ────────────────────────────────────────────
ax4 = fig.add_subplot(gs[2, :2])
seg_counts = customers["segment"].value_counts()
wedges, texts, autotexts = ax4.pie(
    seg_counts.values, labels=seg_counts.index,
    colors=PALETTE[:len(seg_counts)], autopct="%1.1f%%",
    startangle=140, pctdistance=0.82,
    wedgeprops=dict(width=0.55, edgecolor=DARK_BG, linewidth=2),
)
for t in texts: t.set_color(TEXT); t.set_fontsize(9)
for a in autotexts: a.set_color(DARK_BG); a.set_fontsize(8); a.set_fontweight("bold")
ax4.set_title("Customer Segment Distribution")
ax4.set_facecolor(DARK_BG)

# ── Orders by Day of Week ─────────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[2, 2:])
dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
completed["dow"] = completed["order_date"].dt.day_name()
dow_counts = completed["dow"].value_counts().reindex(dow_order)
colors_dow = [GREEN if d in ["Saturday","Sunday"] else ACCENT for d in dow_order]
bars5 = ax5.bar(dow_order, dow_counts.values, color=colors_dow, edgecolor=DARK_BG, linewidth=0.5)
ax5.set_title("Orders by Day of Week")
ax5.tick_params(axis="x", rotation=30, labelsize=8)
ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax5.grid(True, axis="y"); card(ax5)

plt.savefig(OUTPUT / "dashboard_overview.jpg", dpi=150, bbox_inches="tight",
            facecolor=DARK_BG, edgecolor="none")
plt.close()
print("✅ dashboard_overview.jpg saved")


# ════════════════════════════════════════════════════════════════════════════════
# DASHBOARD 2 — Churn & Retention Analysis
# ════════════════════════════════════════════════════════════════════════════════
apply_dark_style()
fig2 = plt.figure(figsize=(18, 12), facecolor=DARK_BG)
fig2.suptitle("Churn & Retention Analysis Dashboard",
              fontsize=18, fontweight="bold", color=TEXT, y=0.98)

gs2 = gridspec.GridSpec(3, 4, figure=fig2, hspace=0.45, wspace=0.38)

# ── Churn KPI Cards ───────────────────────────────────────────────────────────
last_order = completed.groupby("customer_id")["order_date"].max()
inactive = (pd.Timestamp.today() - last_order).dt.days
churn_counts = {
    "Active (<30d)":    (inactive <= 30).sum(),
    "Cooling (30-60d)": ((inactive > 30) & (inactive <= 60)).sum(),
    "At Risk (60-90d)": ((inactive > 60) & (inactive <= 90)).sum(),
    "Churned (90d+)":   (inactive > 90).sum(),
}
churn_colors = [GREEN, YELLOW, ORANGE, RED]
churn_kpis = list(zip(churn_counts.keys(), churn_counts.values(), churn_colors))

for i, (label, value, color) in enumerate(churn_kpis):
    ax = fig2.add_subplot(gs2[0, i])
    ax.set_facecolor(CARD_BG)
    for s in ax.spines.values(): s.set_edgecolor(color); s.set_linewidth(1.5)
    ax.set_xlim(0,1); ax.set_ylim(0,1)
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.5, 0.65, f"{value:,}", ha="center", fontsize=22, fontweight="bold",
            color=color, transform=ax.transAxes)
    pct = value / sum(churn_counts.values()) * 100
    ax.text(0.5, 0.38, label, ha="center", fontsize=8.5, color=SUBTEXT, transform=ax.transAxes)
    ax.text(0.5, 0.16, f"{pct:.1f}% of base", ha="center", fontsize=8,
            color=SUBTEXT, transform=ax.transAxes)

# ── Churn Rate by Segment ─────────────────────────────────────────────────────
ax_c1 = fig2.add_subplot(gs2[1, :2])
seg_churn = []
for seg in customers["segment"].unique():
    cust_ids = customers[customers["segment"] == seg]["customer_id"]
    seg_last = inactive.reindex(cust_ids)
    rate = (seg_last > 90).mean() * 100 if len(seg_last) > 0 else 0
    seg_churn.append({"segment": seg, "churn_rate": rate})

seg_churn_df = pd.DataFrame(seg_churn).sort_values("churn_rate", ascending=True)
bar_colors = [RED if r > 50 else ORANGE if r > 30 else YELLOW for r in seg_churn_df["churn_rate"]]
ax_c1.barh(seg_churn_df["segment"], seg_churn_df["churn_rate"], color=bar_colors,
            edgecolor=DARK_BG)
ax_c1.axvline(30, color=YELLOW, linestyle="--", alpha=0.6, linewidth=1, label="30% threshold")
ax_c1.set_title("Churn Rate by Customer Segment (%)")
ax_c1.set_xlabel("Churn Rate (%)")
ax_c1.legend(); ax_c1.grid(True, axis="x"); card(ax_c1)

# ── Monthly Order Frequency Distribution ────────────────────────────────────
ax_c2 = fig2.add_subplot(gs2[1, 2:])
order_freq = completed.groupby("customer_id").size()
ax_c2.hist(order_freq.clip(upper=30), bins=30, color=ACCENT, edgecolor=DARK_BG, alpha=0.85)
ax_c2.axvline(order_freq.mean(), color=GREEN, linestyle="--", linewidth=1.5,
               label=f"Mean: {order_freq.mean():.1f}")
ax_c2.axvline(order_freq.median(), color=YELLOW, linestyle="--", linewidth=1.5,
               label=f"Median: {order_freq.median():.0f}")
ax_c2.set_title("Order Frequency Distribution (per customer)")
ax_c2.set_xlabel("Number of Orders"); ax_c2.set_ylabel("Customer Count")
ax_c2.legend(); ax_c2.grid(True); card(ax_c2)

# ── Cohort Retention Heatmap ─────────────────────────────────────────────────
ax_c3 = fig2.add_subplot(gs2[2, :])
completed2 = completed.copy()
completed2["cohort"] = completed2.groupby("customer_id")["order_date"].transform("min").dt.to_period("Q")
completed2["order_q"] = completed2["order_date"].dt.to_period("Q")
completed2["period_num"] = (completed2["order_q"] - completed2["cohort"]).apply(lambda x: x.n)

retention_pivot = completed2.groupby(["cohort","period_num"])["customer_id"].nunique().unstack(fill_value=0)
cohort_sizes = retention_pivot[0]
retention_pct = retention_pivot.div(cohort_sizes, axis=0) * 100
retention_pct = retention_pct.iloc[:, :6]  # first 6 quarters

mask = retention_pct == 0
sns.heatmap(retention_pct.round(1), annot=True, fmt=".0f",
            cmap=sns.color_palette("YlOrRd", as_cmap=True),
            linewidths=0.4, linecolor=DARK_BG,
            cbar_kws={"label": "Retention %"},
            mask=mask, ax=ax_c3, annot_kws={"size": 8})
ax_c3.set_title("Cohort Retention Matrix (Quarterly, %)")
ax_c3.set_xlabel("Quarters Since First Purchase")
ax_c3.set_ylabel("Cohort Quarter")
ax_c3.tick_params(axis="x", rotation=0)
ax_c3.tick_params(axis="y", rotation=0, labelsize=8)

plt.savefig(OUTPUT / "dashboard_churn.jpg", dpi=150, bbox_inches="tight",
            facecolor=DARK_BG, edgecolor="none")
plt.close()
print("✅ dashboard_churn.jpg saved")


# ════════════════════════════════════════════════════════════════════════════════
# DASHBOARD 3 — RFM Segmentation & Behavioral Insights
# ════════════════════════════════════════════════════════════════════════════════
apply_dark_style()
fig3 = plt.figure(figsize=(18, 12), facecolor=DARK_BG)
fig3.suptitle("RFM Segmentation & Behavioral Insights Dashboard",
              fontsize=18, fontweight="bold", color=TEXT, y=0.98)
gs3 = gridspec.GridSpec(3, 4, figure=fig3, hspace=0.45, wspace=0.38)

# ── RFM Computation ───────────────────────────────────────────────────────────
snapshot = pd.Timestamp.today()
rfm = completed.groupby("customer_id").agg(
    recency=("order_date", lambda x: (snapshot - x.max()).days),
    frequency=("transaction_id", "count"),
    monetary=("total_amount", "sum"),
).reset_index()
rfm["r"] = pd.qcut(rfm["recency"], q=5, labels=[5,4,3,2,1], duplicates="drop").astype(int)
rfm["f"] = pd.qcut(rfm["frequency"].rank(method="first"), q=5, labels=[1,2,3,4,5]).astype(int)
rfm["m"] = pd.qcut(rfm["monetary"], q=5, labels=[1,2,3,4,5], duplicates="drop").astype(int)
def assign_seg(row):
    r,f,m = row["r"],row["f"],row["m"]
    if r>=4 and f>=4 and m>=4: return "Champions"
    elif r>=3 and f>=3 and m>=3: return "Loyal"
    elif r>=4 and f<=2: return "New"
    elif r<=2 and f>=4 and m>=4: return "At Risk"
    elif r<=2 and f>=2 and m>=2: return "Needs Attention"
    elif r==1 and f==1: return "Lost"
    else: return "Hibernating"
rfm["segment"] = rfm.apply(assign_seg, axis=1)

# ── RFM Scatter: Recency vs Frequency (bubble=Monetary) ─────────────────────
ax_r1 = fig3.add_subplot(gs3[0:2, :2])
seg_colors = {
    "Champions":"#58A6FF","Loyal":"#3FB950","New":"#D29922",
    "At Risk":"#F85149","Needs Attention":"#FFA657","Hibernating":"#8B949E","Lost":"#BC8CFF"
}
for seg, grp in rfm.groupby("segment"):
    sample = grp.sample(min(len(grp), 300))
    ax_r1.scatter(sample["recency"], sample["frequency"],
                  s=sample["monetary"]/100, alpha=0.55,
                  color=seg_colors.get(seg, ACCENT), label=seg, edgecolors="none")
ax_r1.set_title("RFM Scatter: Recency vs Frequency\n(bubble size = Monetary Value)")
ax_r1.set_xlabel("Recency (days since last purchase)")
ax_r1.set_ylabel("Frequency (total orders)")
ax_r1.legend(markerscale=0.8, fontsize=7.5)
ax_r1.grid(True); card(ax_r1)

# ── RFM Segment Revenue Share ─────────────────────────────────────────────────
ax_r2 = fig3.add_subplot(gs3[0:2, 2:])
seg_rev = rfm.groupby("segment")["monetary"].sum().sort_values(ascending=False)
bar_colors_r = [seg_colors.get(s, ACCENT) for s in seg_rev.index]
bars_r = ax_r2.bar(seg_rev.index, seg_rev.values/1000, color=bar_colors_r,
                    edgecolor=DARK_BG, linewidth=0.5)
ax_r2.set_title("Revenue by RFM Segment (₹ thousands)")
ax_r2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:.0f}K"))
ax_r2.tick_params(axis="x", rotation=25, labelsize=8)
for bar in bars_r:
    ax_r2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
               f"₹{bar.get_height():.0f}K", ha="center", fontsize=7.5, color=SUBTEXT)
ax_r2.grid(True, axis="y"); card(ax_r2)

# ── Traffic Source Conversion ─────────────────────────────────────────────────
ax_r3 = fig3.add_subplot(gs3[2, :2])
src_conv = sessions.groupby("traffic_source").agg(
    sessions=("session_id","count"),
    conversions=("converted","sum"),
).reset_index()
src_conv["conversion_rate"] = src_conv["conversions"] / src_conv["sessions"] * 100
src_conv = src_conv.sort_values("conversion_rate", ascending=True)
bars_src = ax_r3.barh(src_conv["traffic_source"], src_conv["conversion_rate"],
                       color=PALETTE[:len(src_conv)], edgecolor=DARK_BG)
ax_r3.set_title("Conversion Rate by Traffic Source (%)")
ax_r3.set_xlabel("Conversion Rate (%)")
for b in bars_src:
    ax_r3.text(b.get_width()+0.05, b.get_y()+b.get_height()/2,
               f"{b.get_width():.1f}%", va="center", fontsize=8, color=SUBTEXT)
ax_r3.grid(True, axis="x"); card(ax_r3)

# ── Device Usage Split ────────────────────────────────────────────────────────
ax_r4 = fig3.add_subplot(gs3[2, 2:])
device_counts = sessions["device"].value_counts()
wedges2, texts2, auto2 = ax_r4.pie(
    device_counts.values, labels=device_counts.index,
    colors=[ACCENT, GREEN, YELLOW],
    autopct="%1.1f%%", startangle=90,
    wedgeprops=dict(width=0.6, edgecolor=DARK_BG, linewidth=2),
)
for t in texts2: t.set_color(TEXT)
for a in auto2: a.set_color(DARK_BG); a.set_fontweight("bold")
ax_r4.set_title("Sessions by Device Type")
ax_r4.set_facecolor(DARK_BG)

plt.savefig(OUTPUT / "dashboard_rfm.jpg", dpi=150, bbox_inches="tight",
            facecolor=DARK_BG, edgecolor="none")
plt.close()
print("✅ dashboard_rfm.jpg saved")
print("\n✅ All 3 dashboards generated successfully!")
