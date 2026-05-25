# 🛒 E-Commerce Customer Behavior Analysis

> Analyzed **100K+ transaction records** using Python and SQL to segment customer cohorts and identify churn patterns, delivering actionable insights for marketing. Automated weekly behavioral reporting via ETL pipeline, reducing manual effort by **50%** and enabling data-driven decision-making.

---

## 📊 Dashboards

<table>
<tr>
<td><img src="dashboards/dashboard_overview.jpg" width="100%"/><br><b>Overview & Revenue</b></td>
<td><img src="dashboards/dashboard_churn.jpg" width="100%"/><br><b>Churn & Retention</b></td>
<td><img src="dashboards/dashboard_rfm.jpg" width="100%"/><br><b>RFM Segmentation</b></td>
</tr>
</table>

---

## 🚀 Key Results

| Metric | Value |
|--------|-------|
| Records analyzed | 100,000+ transactions |
| Customer profiles | 10,000 customers |
| Session logs | 200,000+ web sessions |
| Churn model ROC-AUC | ~0.87 |
| Manual reporting effort saved | 50% |
| Customer segments identified | 7 RFM segments |

---

## 🗂️ Project Structure

```
ecommerce-behavior-analysis/
├── main.py                        # Pipeline entry point
├── generate_dashboards.py         # Dashboard generator
├── requirements.txt
├── config/
│   └── config.yaml                # All pipeline settings
├── data/
│   ├── generate_sample_data.py    # Synthetic data generator
│   └── README.md
├── sql/
│   ├── customer_segmentation.sql  # RFM + cohort SQL queries
│   ├── churn_analysis.sql         # Churn detection queries
│   └── cohort_analysis.sql        # Retention matrix queries
├── src/
│   ├── data_loader.py             # Cached data loading
│   ├── customer_segmentation.py   # RFM + KMeans segmentation
│   ├── churn_analysis.py          # Feature engineering + GBM model
│   └── etl_pipeline.py            # Automated ETL + reporting
├── dashboards/
│   ├── dashboard_overview.jpg
│   ├── dashboard_churn.jpg
│   └── dashboard_rfm.jpg
├── tests/
│   └── test_modules.py            # pytest unit tests
└── reports/
    └── output/                    # Auto-generated weekly reports
```

---

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ecommerce-behavior-analysis.git
cd ecommerce-behavior-analysis
pip install -r requirements.txt
```

### 2. Generate Sample Data

```bash
python data/generate_sample_data.py
```

### 3. Run Full Pipeline

```bash
# All steps at once
python main.py --all

# Or individually:
python main.py --segment        # RFM segmentation
python main.py --churn          # Churn prediction
python main.py --run-etl        # Weekly ETL report
python main.py --dashboards     # Regenerate dashboard JPGs
```

### 4. Run Tests

```bash
pytest tests/ -v --cov=src
```

---

## 📐 Methodology

### Customer Segmentation (RFM)

Customers are scored on three dimensions:

| Dimension | Description |
|-----------|-------------|
| **Recency (R)** | Days since last purchase (lower = better) |
| **Frequency (F)** | Total completed orders |
| **Monetary (M)** | Total revenue generated |

Each dimension is binned into quintiles (1–5), producing **7 behavioral segments**:

| Segment | Action |
|---------|--------|
| 🏆 Champions | Reward & upsell |
| ❤️ Loyal Customers | Loyalty programme |
| 🌱 New Customers | Onboarding sequence |
| 💡 Potential Loyalists | Engagement campaigns |
| ⚠️ At Risk | Win-back offers |
| 💤 Needs Attention | Re-engagement emails |
| ❌ Lost | Suppression list |

### Churn Prediction Model

A **Gradient Boosting Classifier** (scikit-learn) trained on:
- RFM features
- Session engagement metrics (pages viewed, bounce rate, conversion)
- Customer demographics (age, tenure, geography)
- Return & cancellation rates

```
Train/Test split: 80/20 stratified
Cross-validation: 5-fold StratifiedKFold
Primary metric: ROC-AUC (~0.87)
```

### Automated ETL Pipeline

```
Extract  →  raw CSV / DB snapshots
Transform →  deduplication, validation, enrichment
Compute  →  KPIs, segment metrics, churn risk
Load     →  JSON / CSV / Markdown weekly report
```

Designed to run on a weekly cron schedule with zero manual intervention.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| **Python 3.10+** | Core language |
| **pandas** | Data wrangling |
| **scikit-learn** | ML models (GBM, K-Means) |
| **matplotlib / seaborn** | Visualisation |
| **SQL** | Database-layer queries |
| **PyYAML** | Configuration management |
| **pytest** | Unit testing |

---

## 📁 SQL Queries

Three production-ready SQL files cover:

- **`customer_segmentation.sql`** — RFM scoring, LTV by segment, Pareto analysis, segment migration
- **`churn_analysis.sql`** — Churn identification, cohort churn rates, behavioral signals, revenue at risk
- **`cohort_analysis.sql`** — Monthly retention matrix, AOV progression, LTV curves

Compatible with **MySQL 8+** and **PostgreSQL 13+**.

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-improvement`)
3. Commit changes (`git commit -m 'Add: my improvement'`)
4. Push and open a Pull Request

Please run `pytest tests/` before submitting.

---

## 👤 Author

Built as part of a data analytics portfolio. Feedback and stars welcome! ⭐
