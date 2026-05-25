"""
Automated Weekly ETL Pipeline
Extracts, transforms, and loads e-commerce behavioral data.
Generates weekly behavioral reports and sends summary metrics.
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
import yaml

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ──────────────────────────────────────────────────────────────────────────────
# EXTRACT
# ──────────────────────────────────────────────────────────────────────────────
class DataExtractor:
    """Reads raw CSV / database snapshots for the reporting window."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def load_transactions(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        path = self.data_dir / "transactions.csv"
        logger.info(f"Loading transactions from {path}")
        df = pd.read_csv(path, parse_dates=["order_date"])

        if start_date:
            df = df[df["order_date"] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df["order_date"] <= pd.Timestamp(end_date)]

        logger.info(f"Loaded {len(df):,} transaction records.")
        return df

    def load_customers(self) -> pd.DataFrame:
        path = self.data_dir / "customers.csv"
        logger.info(f"Loading customers from {path}")
        df = pd.read_csv(path, parse_dates=["signup_date"])
        logger.info(f"Loaded {len(df):,} customer records.")
        return df

    def load_sessions(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        path = self.data_dir / "sessions.csv"
        if not path.exists():
            logger.warning("sessions.csv not found — skipping session data.")
            return pd.DataFrame()

        logger.info(f"Loading sessions from {path}")
        df = pd.read_csv(path, parse_dates=["session_date"])

        if start_date:
            df = df[df["session_date"] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df["session_date"] <= pd.Timestamp(end_date)]

        logger.info(f"Loaded {len(df):,} session records.")
        return df


# ──────────────────────────────────────────────────────────────────────────────
# TRANSFORM
# ──────────────────────────────────────────────────────────────────────────────
class DataTransformer:
    """Cleans, validates, and enriches raw data."""

    REQUIRED_TXN_COLS = {"transaction_id", "customer_id", "order_date", "total_amount", "status"}
    REQUIRED_CUST_COLS = {"customer_id", "signup_date", "segment"}

    @staticmethod
    def validate(df: pd.DataFrame, required_cols: set, name: str) -> pd.DataFrame:
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"[{name}] Missing required columns: {missing}")
        null_counts = df[list(required_cols)].isnull().sum()
        if null_counts.any():
            logger.warning(f"[{name}] Null values detected:\n{null_counts[null_counts > 0]}")
        return df

    def transform_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Transforming transactions...")
        df = self.validate(df, self.REQUIRED_TXN_COLS, "transactions")

        # Dedup
        before = len(df)
        df = df.drop_duplicates(subset=["transaction_id"])
        logger.info(f"  Removed {before - len(df):,} duplicate transactions.")

        # Filter invalid amounts
        df = df[df["total_amount"] > 0]

        # Derived columns
        df["week"] = df["order_date"].dt.isocalendar().week.astype(int)
        df["month"] = df["order_date"].dt.to_period("M").astype(str)
        df["quarter"] = df["order_date"].dt.to_period("Q").astype(str)
        df["day_of_week"] = df["order_date"].dt.day_name()
        df["is_weekend"] = df["order_date"].dt.dayofweek >= 5

        logger.info(f"  Transactions after cleaning: {len(df):,}")
        return df

    def transform_customers(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Transforming customers...")
        df = self.validate(df, self.REQUIRED_CUST_COLS, "customers")
        df["tenure_days"] = (pd.Timestamp.today() - df["signup_date"]).dt.days
        df["tenure_band"] = pd.cut(
            df["tenure_days"],
            bins=[0, 90, 365, 730, float("inf")],
            labels=["New (<3m)", "Growing (3-12m)", "Established (1-2y)", "Veteran (2y+)"],
        )
        return df

    def enrich_transactions(self, txn: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
        logger.info("Enriching transactions with customer attributes...")
        return txn.merge(
            customers[["customer_id", "segment", "tenure_band", "country"]],
            on="customer_id", how="left",
        )


# ──────────────────────────────────────────────────────────────────────────────
# COMPUTE METRICS
# ──────────────────────────────────────────────────────────────────────────────
class MetricsComputer:
    """Computes weekly KPIs for behavioral reporting."""

    @staticmethod
    def weekly_summary(txn: pd.DataFrame, week: int) -> dict:
        w = txn[(txn["week"] == week) & (txn["status"] == "Completed")]
        revenue = w["total_amount"].sum()
        orders = len(w)
        customers = w["customer_id"].nunique()
        aov = revenue / orders if orders > 0 else 0
        return {
            "week": week,
            "revenue": round(revenue, 2),
            "orders": orders,
            "unique_customers": customers,
            "avg_order_value": round(aov, 2),
        }

    @staticmethod
    def category_breakdown(txn: pd.DataFrame) -> pd.DataFrame:
        completed = txn[txn["status"] == "Completed"]
        return (
            completed.groupby("category")
            .agg(revenue=("total_amount", "sum"), orders=("transaction_id", "count"))
            .assign(avg_order_value=lambda d: (d["revenue"] / d["orders"]).round(2))
            .sort_values("revenue", ascending=False)
            .reset_index()
        )

    @staticmethod
    def segment_weekly_kpis(txn: pd.DataFrame) -> pd.DataFrame:
        completed = txn[txn["status"] == "Completed"]
        if "segment" not in completed.columns:
            return pd.DataFrame()
        return (
            completed.groupby(["week", "segment"])
            .agg(revenue=("total_amount", "sum"), customers=("customer_id", "nunique"))
            .reset_index()
        )

    @staticmethod
    def churn_risk_summary(customers: pd.DataFrame, txn: pd.DataFrame,
                            threshold_days: int = 90) -> pd.DataFrame:
        last_txn = (
            txn[txn["status"] == "Completed"]
            .groupby("customer_id")["order_date"]
            .max()
            .rename("last_order")
        )
        df = customers.join(last_txn, on="customer_id")
        df["days_inactive"] = (pd.Timestamp.today() - df["last_order"]).dt.days
        df["churn_risk"] = pd.cut(
            df["days_inactive"],
            bins=[0, 30, 60, 90, float("inf")],
            labels=["Active", "Cooling", "At Risk", "Churned"],
        )
        return df.groupby("churn_risk")["customer_id"].count().rename("count").reset_index()


# ──────────────────────────────────────────────────────────────────────────────
# LOAD / REPORT
# ──────────────────────────────────────────────────────────────────────────────
class ReportLoader:
    """Saves processed metrics and generates weekly report files."""

    def __init__(self, output_dir: str = "reports/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, data: dict, filename: str):
        path = self.output_dir / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved: {path}")

    def save_csv(self, df: pd.DataFrame, filename: str):
        path = self.output_dir / filename
        df.to_csv(path, index=False)
        logger.info(f"Saved: {path}")

    def generate_weekly_report(self, summary: dict, category_df: pd.DataFrame,
                                segment_df: pd.DataFrame, churn_df: pd.DataFrame,
                                week: int):
        report_path = self.output_dir / f"weekly_report_week{week:02d}.md"
        lines = [
            f"# Weekly Behavioral Report — Week {week}",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "## 📊 Key Metrics",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Revenue | ₹{summary['revenue']:,.2f} |",
            f"| Total Orders | {summary['orders']:,} |",
            f"| Unique Customers | {summary['unique_customers']:,} |",
            f"| Avg Order Value | ₹{summary['avg_order_value']:,.2f} |",
            "",
            "## 🛒 Category Breakdown",
            category_df[["category", "revenue", "orders"]].to_markdown(index=False),
            "",
            "## 👥 Customer Churn Risk",
            churn_df.to_markdown(index=False),
            "",
        ]
        with open(report_path, "w") as f:
            f.write("\n".join(lines))
        logger.info(f"Weekly report saved: {report_path}")


# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────────────
class ETLPipeline:
    """Orchestrates the full extract → transform → compute → load workflow."""

    def __init__(self, config_path: str = "config/config.yaml"):
        cfg = load_config(config_path)
        self.extractor = DataExtractor(cfg.get("data_dir", "data"))
        self.transformer = DataTransformer()
        self.metrics = MetricsComputer()
        self.loader = ReportLoader(cfg.get("output_dir", "reports/output"))
        self.churn_threshold = cfg.get("churn_threshold_days", 90)

    def run(self, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """Execute the full ETL pipeline for a given date range."""
        if not end_date:
            end_date = datetime.today().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")

        logger.info(f"▶  ETL Pipeline starting  [{start_date} → {end_date}]")

        # ── Extract ──────────────────────────────────────
        raw_txn = self.extractor.load_transactions(start_date, end_date)
        raw_customers = self.extractor.load_customers()

        # ── Transform ────────────────────────────────────
        txn = self.transformer.transform_transactions(raw_txn)
        customers = self.transformer.transform_customers(raw_customers)
        txn_enriched = self.transformer.enrich_transactions(txn, customers)

        # ── Compute ──────────────────────────────────────
        current_week = datetime.today().isocalendar()[1]
        summary = self.metrics.weekly_summary(txn_enriched, current_week)
        cat_breakdown = self.metrics.category_breakdown(txn_enriched)
        seg_kpis = self.metrics.segment_weekly_kpis(txn_enriched)
        churn_summary = self.metrics.churn_risk_summary(customers, txn, self.churn_threshold)

        # ── Load ─────────────────────────────────────────
        self.loader.save_json(summary, f"summary_week{current_week:02d}.json")
        self.loader.save_csv(cat_breakdown, f"category_breakdown_week{current_week:02d}.csv")
        self.loader.save_csv(seg_kpis, f"segment_kpis_week{current_week:02d}.csv")
        self.loader.save_csv(churn_summary, f"churn_risk_week{current_week:02d}.csv")
        self.loader.generate_weekly_report(summary, cat_breakdown, seg_kpis,
                                            churn_summary, current_week)

        logger.info("✅  ETL Pipeline completed successfully.")
        return {
            "summary": summary,
            "category_breakdown": cat_breakdown,
            "churn_summary": churn_summary,
        }


if __name__ == "__main__":
    pipeline = ETLPipeline()
    pipeline.run()
