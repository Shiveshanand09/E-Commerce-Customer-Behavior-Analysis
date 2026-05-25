"""
Churn Analysis Module
Detects at-risk customers and trains a churn prediction model.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix,
    precision_recall_curve, average_precision_score,
)
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings("ignore")


CHURN_DAYS_THRESHOLD = 90  # days without purchase → churned


class ChurnFeatureBuilder:
    """Builds a feature matrix for churn modelling from raw transaction and session data."""

    def __init__(self, churn_threshold_days: int = CHURN_DAYS_THRESHOLD,
                 snapshot_date: str = None):
        self.threshold = churn_threshold_days
        self.snapshot_date = pd.Timestamp(snapshot_date) if snapshot_date else pd.Timestamp.today()

    def build(self, customers: pd.DataFrame, transactions: pd.DataFrame,
              sessions: pd.DataFrame = None) -> pd.DataFrame:
        """
        Construct a feature matrix with one row per customer.

        Parameters
        ----------
        customers    : customer profile table
        transactions : transaction records (all statuses)
        sessions     : website session data (optional)

        Returns
        -------
        pd.DataFrame with feature columns + 'churned' label
        """
        txn = transactions.copy()
        txn["order_date"] = pd.to_datetime(txn["order_date"])

        completed = txn[txn["status"] == "Completed"]

        # ── Transaction features ─────────────────────────────────
        txn_features = completed.groupby("customer_id").agg(
            total_orders=("transaction_id", "count"),
            total_revenue=("total_amount", "sum"),
            avg_order_value=("total_amount", "mean"),
            max_order_value=("total_amount", "max"),
            unique_categories=("category", "nunique"),
            recency_days=("order_date", lambda x: (self.snapshot_date - x.max()).days),
            first_order_days=("order_date", lambda x: (self.snapshot_date - x.min()).days),
            avg_discount=("discount_pct", "mean"),
        ).reset_index()

        txn_features["order_frequency"] = (
            txn_features["total_orders"] / (txn_features["first_order_days"] / 30 + 1)
        )

        # ── Return / cancellation features ───────────────────────
        neg = txn.groupby("customer_id").agg(
            returns=("status", lambda x: (x == "Returned").sum()),
            cancellations=("status", lambda x: (x == "Cancelled").sum()),
        ).reset_index()

        txn_features = txn_features.merge(neg, on="customer_id", how="left")
        txn_features["return_rate"] = (
            txn_features["returns"] / txn_features["total_orders"].clip(lower=1)
        )

        # ── Customer profile features ─────────────────────────────
        customers = customers.copy()
        customers["signup_date"] = pd.to_datetime(customers["signup_date"])
        customers["tenure_days"] = (self.snapshot_date - customers["signup_date"]).dt.days

        features = txn_features.merge(
            customers[["customer_id", "age", "gender", "country", "tenure_days"]],
            on="customer_id", how="left",
        )

        # ── Session features (optional) ───────────────────────────
        if sessions is not None:
            sess = sessions.copy()
            sess_features = sess.groupby("customer_id").agg(
                total_sessions=("session_id", "count"),
                avg_session_duration=("session_duration_sec", "mean"),
                avg_pages_viewed=("pages_viewed", "mean"),
                bounce_rate=("bounced", "mean"),
                conversion_rate=("converted", "mean"),
            ).reset_index()
            features = features.merge(sess_features, on="customer_id", how="left")

        # ── One-hot encode categoricals ───────────────────────────
        features = pd.get_dummies(features, columns=["gender", "country"], drop_first=True)

        # ── Churn label ───────────────────────────────────────────
        features["churned"] = (features["recency_days"] > self.threshold).astype(int)

        return features


class ChurnPredictor:
    """Gradient Boosting churn prediction model with cross-validated evaluation."""

    def __init__(self, model_type: str = "gbm"):
        models = {
            "gbm": GradientBoostingClassifier(n_estimators=200, learning_rate=0.05,
                                               max_depth=4, random_state=42),
            "rf": RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42),
            "lr": LogisticRegression(max_iter=1000, C=0.1, random_state=42),
        }
        self.model_type = model_type
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", models[model_type]),
        ])
        self.feature_cols = None
        self.is_trained = False

    def fit(self, features: pd.DataFrame, target_col: str = "churned"):
        """Train the churn model."""
        drop_cols = [target_col, "customer_id"]
        self.feature_cols = [c for c in features.columns if c not in drop_cols
                              and features[c].dtype in [np.float64, np.int64, np.uint8, bool]]

        X = features[self.feature_cols].fillna(0)
        y = features[target_col]

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )

        self.pipeline.fit(self.X_train, self.y_train)
        self.is_trained = True
        return self

    def evaluate(self) -> dict:
        """Return evaluation metrics on the held-out test set."""
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call fit() first.")

        y_pred = self.pipeline.predict(self.X_test)
        y_proba = self.pipeline.predict_proba(self.X_test)[:, 1]

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_auc = cross_val_score(self.pipeline, self.X_train, self.y_train,
                                  scoring="roc_auc", cv=cv)

        return {
            "roc_auc": round(roc_auc_score(self.y_test, y_proba), 4),
            "avg_precision": round(average_precision_score(self.y_test, y_proba), 4),
            "cv_auc_mean": round(cv_auc.mean(), 4),
            "cv_auc_std": round(cv_auc.std(), 4),
            "classification_report": classification_report(self.y_test, y_pred),
            "confusion_matrix": confusion_matrix(self.y_test, y_pred),
        }

    def predict_churn_proba(self, new_data: pd.DataFrame) -> pd.Series:
        """Return churn probability for new customers."""
        X = new_data[self.feature_cols].fillna(0)
        return pd.Series(self.pipeline.predict_proba(X)[:, 1],
                          index=new_data.index, name="churn_probability")

    def feature_importance(self) -> pd.DataFrame:
        """Return sorted feature importances (GBM / RF only)."""
        clf = self.pipeline.named_steps["clf"]
        if hasattr(clf, "feature_importances_"):
            return (
                pd.DataFrame({
                    "feature": self.feature_cols,
                    "importance": clf.feature_importances_,
                })
                .sort_values("importance", ascending=False)
                .reset_index(drop=True)
            )
        raise AttributeError(f"Model type '{self.model_type}' does not expose feature importances.")
