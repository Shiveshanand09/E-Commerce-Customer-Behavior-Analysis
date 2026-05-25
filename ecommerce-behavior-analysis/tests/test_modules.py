"""
Unit tests for E-Commerce Customer Behavior Analysis modules.
Run with: pytest tests/ -v --cov=src
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.customer_segmentation import RFMAnalyzer, KMeansSegmenter, CohortAnalyzer
from src.churn_analysis import ChurnFeatureBuilder, ChurnPredictor


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def sample_transactions():
    np.random.seed(42)
    n = 500
    customer_ids = [f"CUST{i:04d}" for i in np.random.randint(1, 51, n)]
    return pd.DataFrame({
        "transaction_id": [f"TXN{i:06d}" for i in range(n)],
        "customer_id": customer_ids,
        "order_date": pd.date_range("2023-01-01", periods=n, freq="12h"),
        "total_amount": np.random.lognormal(5, 1, n),
        "discount_pct": np.random.uniform(0, 40, n),
        "category": np.random.choice(["Electronics","Clothing","Books"], n),
        "status": np.random.choice(["Completed","Returned","Cancelled"],
                                    n, p=[0.85, 0.08, 0.07]),
    })


@pytest.fixture
def sample_customers():
    np.random.seed(42)
    n = 50
    return pd.DataFrame({
        "customer_id": [f"CUST{i:04d}" for i in range(1, n+1)],
        "signup_date": pd.date_range("2022-01-01", periods=n, freq="7D"),
        "age": np.random.randint(18, 65, n),
        "gender": np.random.choice(["Male","Female"], n),
        "country": np.random.choice(["India","USA","UK"], n),
        "segment": np.random.choice(["Premium","Regular","Occasional","At-Risk"], n),
        "lifetime_value": np.random.lognormal(5.5, 1, n),
    })


# ── RFM Tests ────────────────────────────────────────────────────────────────
class TestRFMAnalyzer:
    def test_compute_rfm_returns_dataframe(self, sample_transactions):
        analyzer = RFMAnalyzer()
        result = analyzer.compute_rfm(sample_transactions)
        assert isinstance(result, pd.DataFrame)

    def test_rfm_columns_present(self, sample_transactions):
        analyzer = RFMAnalyzer()
        result = analyzer.compute_rfm(sample_transactions)
        for col in ["customer_id", "recency", "frequency", "monetary", "r", "f", "m", "segment"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_rfm_scores_in_range(self, sample_transactions):
        analyzer = RFMAnalyzer()
        result = analyzer.compute_rfm(sample_transactions)
        assert result["r"].between(1, 5).all()
        assert result["f"].between(1, 5).all()
        assert result["m"].between(1, 5).all()

    def test_segment_summary_runs(self, sample_transactions):
        analyzer = RFMAnalyzer()
        analyzer.compute_rfm(sample_transactions)
        summary = analyzer.segment_summary()
        assert len(summary) > 0
        assert "total_revenue" in summary.columns

    def test_only_completed_used(self, sample_transactions):
        analyzer = RFMAnalyzer()
        result = analyzer.compute_rfm(sample_transactions)
        completed_customers = sample_transactions[
            sample_transactions["status"] == "Completed"]["customer_id"].nunique()
        assert len(result) <= completed_customers


# ── KMeans Tests ──────────────────────────────────────────────────────────────
class TestKMeansSegmenter:
    def test_fit_and_labels(self, sample_transactions):
        analyzer = RFMAnalyzer()
        rfm = analyzer.compute_rfm(sample_transactions)
        km = KMeansSegmenter(n_clusters=3)
        km.fit(rfm)
        assert km.labels is not None
        assert len(km.labels) == len(rfm)

    def test_silhouette_score(self, sample_transactions):
        analyzer = RFMAnalyzer()
        rfm = analyzer.compute_rfm(sample_transactions)
        km = KMeansSegmenter(n_clusters=3)
        km.fit(rfm)
        assert 0 <= km.silhouette <= 1

    def test_add_clusters(self, sample_transactions):
        analyzer = RFMAnalyzer()
        rfm = analyzer.compute_rfm(sample_transactions)
        km = KMeansSegmenter(n_clusters=3)
        km.fit(rfm)
        result = km.add_clusters(rfm)
        assert "cluster" in result.columns
        assert result["cluster"].nunique() == 3


# ── Churn Tests ───────────────────────────────────────────────────────────────
class TestChurnFeatureBuilder:
    def test_build_returns_dataframe(self, sample_transactions, sample_customers):
        builder = ChurnFeatureBuilder()
        features = builder.build(sample_customers, sample_transactions)
        assert isinstance(features, pd.DataFrame)

    def test_churned_column_exists(self, sample_transactions, sample_customers):
        builder = ChurnFeatureBuilder()
        features = builder.build(sample_customers, sample_transactions)
        assert "churned" in features.columns

    def test_churned_is_binary(self, sample_transactions, sample_customers):
        builder = ChurnFeatureBuilder()
        features = builder.build(sample_customers, sample_transactions)
        assert features["churned"].isin([0, 1]).all()


class TestChurnPredictor:
    def test_fit_and_evaluate(self, sample_transactions, sample_customers):
        builder = ChurnFeatureBuilder()
        features = builder.build(sample_customers, sample_transactions)
        if features["churned"].sum() < 5:
            pytest.skip("Not enough churn examples in sample.")

        predictor = ChurnPredictor(model_type="rf")
        predictor.fit(features)
        metrics = predictor.evaluate()

        assert "roc_auc" in metrics
        assert 0 <= metrics["roc_auc"] <= 1

    def test_feature_importance(self, sample_transactions, sample_customers):
        builder = ChurnFeatureBuilder()
        features = builder.build(sample_customers, sample_transactions)
        if features["churned"].sum() < 5:
            pytest.skip("Not enough churn examples in sample.")

        predictor = ChurnPredictor(model_type="rf")
        predictor.fit(features)
        fi = predictor.feature_importance()

        assert "feature" in fi.columns
        assert "importance" in fi.columns
        assert fi["importance"].sum() == pytest.approx(1.0, abs=0.01)
