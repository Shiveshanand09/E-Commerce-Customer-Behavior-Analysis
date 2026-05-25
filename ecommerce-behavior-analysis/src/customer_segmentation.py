"""
Customer Segmentation Module
Implements RFM analysis and K-Means clustering for customer cohort identification.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings("ignore")


class RFMAnalyzer:
    """Recency-Frequency-Monetary (RFM) customer segmentation."""

    SEGMENT_MAP = {
        (5, 5, 5): "Champions",
        (4, 4, 4): "Loyal Customers",
        (5, 1, 1): "New Customers",
        (3, 3, 3): "Potential Loyalists",
        (1, 4, 4): "At Risk",
        (1, 1, 1): "Lost",
    }

    def __init__(self, snapshot_date: str = None):
        self.snapshot_date = pd.Timestamp(snapshot_date) if snapshot_date else pd.Timestamp.today()
        self.rfm_table = None
        self.scaler = StandardScaler()

    def compute_rfm(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Compute RFM scores from transaction data.

        Parameters
        ----------
        transactions : pd.DataFrame
            Must contain columns: customer_id, order_date, total_amount, status

        Returns
        -------
        pd.DataFrame  with columns: customer_id, recency, frequency, monetary, r, f, m, segment
        """
        df = transactions[transactions["status"] == "Completed"].copy()
        df["order_date"] = pd.to_datetime(df["order_date"])

        rfm = df.groupby("customer_id").agg(
            recency=("order_date", lambda x: (self.snapshot_date - x.max()).days),
            frequency=("transaction_id", "count"),
            monetary=("total_amount", "sum"),
        ).reset_index()

        rfm["r"] = pd.qcut(rfm["recency"], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)
        rfm["f"] = pd.qcut(rfm["frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
        rfm["m"] = pd.qcut(rfm["monetary"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
        rfm["rfm_score"] = rfm["r"] * 100 + rfm["f"] * 10 + rfm["m"]
        rfm["segment"] = rfm.apply(self._assign_segment, axis=1)

        self.rfm_table = rfm
        return rfm

    @staticmethod
    def _assign_segment(row) -> str:
        r, f, m = row["r"], row["f"], row["m"]
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions"
        elif r >= 3 and f >= 3 and m >= 3:
            return "Loyal Customers"
        elif r >= 4 and f <= 2:
            return "New Customers"
        elif r >= 3 and f >= 1 and m >= 2:
            return "Potential Loyalists"
        elif r <= 2 and f >= 4 and m >= 4:
            return "At Risk"
        elif r <= 2 and f >= 2 and m >= 2:
            return "Needs Attention"
        elif r == 1 and f == 1:
            return "Lost"
        else:
            return "Hibernating"

    def segment_summary(self) -> pd.DataFrame:
        """Return aggregated segment-level statistics."""
        if self.rfm_table is None:
            raise ValueError("Run compute_rfm() first.")
        return (
            self.rfm_table
            .groupby("segment")
            .agg(
                customers=("customer_id", "count"),
                avg_recency=("recency", "mean"),
                avg_frequency=("frequency", "mean"),
                avg_monetary=("monetary", "mean"),
                total_revenue=("monetary", "sum"),
            )
            .round(2)
            .reset_index()
            .sort_values("total_revenue", ascending=False)
        )


class KMeansSegmenter:
    """Unsupervised K-Means customer clustering on scaled RFM features."""

    def __init__(self, n_clusters: int = 5, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        self.scaler = StandardScaler()
        self.labels = None
        self.silhouette = None

    def fit(self, rfm: pd.DataFrame) -> "KMeansSegmenter":
        features = rfm[["recency", "frequency", "monetary"]].copy()
        features_scaled = self.scaler.fit_transform(features)
        self.labels = self.model.fit_predict(features_scaled)
        self.silhouette = silhouette_score(features_scaled, self.labels)
        return self

    def add_clusters(self, rfm: pd.DataFrame) -> pd.DataFrame:
        """Append cluster labels to the RFM DataFrame."""
        result = rfm.copy()
        result["cluster"] = self.labels
        return result

    def optimal_k(self, rfm: pd.DataFrame, k_range: range = range(2, 11)) -> dict:
        """Find optimal K using elbow method and silhouette scores."""
        features_scaled = self.scaler.fit_transform(rfm[["recency", "frequency", "monetary"]])
        inertia, silhouettes = [], []

        for k in k_range:
            km = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
            labels = km.fit_predict(features_scaled)
            inertia.append(km.inertia_)
            silhouettes.append(silhouette_score(features_scaled, labels))

        return {"k": list(k_range), "inertia": inertia, "silhouette": silhouettes}


class CohortAnalyzer:
    """Monthly cohort retention and LTV analysis."""

    def __init__(self):
        self.retention_matrix = None

    def build_retention_matrix(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Build a cohort × month retention matrix.

        Returns
        -------
        pd.DataFrame  pivot table, rows = cohort months, cols = month number (0..N)
        """
        df = transactions[transactions["status"] == "Completed"].copy()
        df["order_date"] = pd.to_datetime(df["order_date"])
        df["order_month"] = df["order_date"].dt.to_period("M")

        cohort_dates = df.groupby("customer_id")["order_month"].min().rename("cohort_month")
        df = df.join(cohort_dates, on="customer_id")
        df["month_number"] = (df["order_month"] - df["cohort_month"]).apply(lambda x: x.n)

        counts = df.groupby(["cohort_month", "month_number"])["customer_id"].nunique().reset_index()
        cohort_sizes = counts[counts["month_number"] == 0].set_index("cohort_month")["customer_id"]

        pivot = counts.pivot(index="cohort_month", columns="month_number", values="customer_id")
        retention = pivot.divide(cohort_sizes, axis=0).round(4) * 100
        self.retention_matrix = retention
        return retention

    def ltv_curve(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """Compute cumulative average revenue per customer by cohort and month."""
        df = transactions[transactions["status"] == "Completed"].copy()
        df["order_date"] = pd.to_datetime(df["order_date"])
        df["order_month"] = df["order_date"].dt.to_period("M")

        cohort_dates = df.groupby("customer_id")["order_month"].min().rename("cohort_month")
        df = df.join(cohort_dates, on="customer_id")
        df["month_number"] = (df["order_month"] - df["cohort_month"]).apply(lambda x: x.n)

        cohort_sizes = df.groupby("cohort_month")["customer_id"].nunique()
        revenue = df.groupby(["cohort_month", "month_number"])["total_amount"].sum()

        ltv = (revenue / cohort_sizes).groupby(level="cohort_month").cumsum().reset_index()
        ltv.columns = ["cohort_month", "month_number", "cumulative_avg_revenue"]
        return ltv
