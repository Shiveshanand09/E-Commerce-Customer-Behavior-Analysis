"""
Main entry point — run the full analysis pipeline end to end.
"""

import logging
import argparse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="E-Commerce Customer Behavior Analysis")
    parser.add_argument("--generate-data", action="store_true",
                        help="Generate synthetic sample data")
    parser.add_argument("--run-etl", action="store_true",
                        help="Run the weekly ETL pipeline")
    parser.add_argument("--segment", action="store_true",
                        help="Run RFM customer segmentation")
    parser.add_argument("--churn", action="store_true",
                        help="Run churn prediction model")
    parser.add_argument("--dashboards", action="store_true",
                        help="Generate dashboard visualisations")
    parser.add_argument("--all", action="store_true",
                        help="Run all steps")
    args = parser.parse_args()

    if args.generate_data or args.all:
        logger.info("── Step 1: Generating sample data ──────────────────")
        from data.generate_sample_data import generate_customers, generate_transactions, generate_sessions
        import pandas as pd
        cust = generate_customers(10000)
        cust.to_csv("data/customers.csv", index=False)
        txn = generate_transactions(cust, 100000)
        txn.to_csv("data/transactions.csv", index=False)
        sess = generate_sessions(cust, 200000)
        sess.to_csv("data/sessions.csv", index=False)
        logger.info("✅ Sample data generated.")

    if args.run_etl or args.all:
        logger.info("── Step 2: Running ETL pipeline ────────────────────")
        from src.etl_pipeline import ETLPipeline
        pipeline = ETLPipeline()
        result = pipeline.run()
        logger.info(f"✅ ETL complete. Revenue this week: ₹{result['summary']['revenue']:,.0f}")

    if args.segment or args.all:
        logger.info("── Step 3: RFM Segmentation ─────────────────────────")
        import pandas as pd
        from src.customer_segmentation import RFMAnalyzer
        txn = pd.read_csv("data/transactions.csv", parse_dates=["order_date"])
        analyzer = RFMAnalyzer()
        rfm = analyzer.compute_rfm(txn)
        summary = analyzer.segment_summary()
        Path("reports/output").mkdir(parents=True, exist_ok=True)
        summary.to_csv("reports/output/rfm_segments.csv", index=False)
        logger.info("✅ RFM segmentation complete:")
        logger.info("\n" + summary[["segment","customers","avg_monetary","total_revenue"]].to_string(index=False))

    if args.churn or args.all:
        logger.info("── Step 4: Churn Prediction ─────────────────────────")
        import pandas as pd
        from src.churn_analysis import ChurnFeatureBuilder, ChurnPredictor
        txn = pd.read_csv("data/transactions.csv", parse_dates=["order_date"])
        cust = pd.read_csv("data/customers.csv", parse_dates=["signup_date"])
        sess = pd.read_csv("data/sessions.csv", parse_dates=["session_date"])

        builder = ChurnFeatureBuilder()
        features = builder.build(cust, txn, sess)

        predictor = ChurnPredictor(model_type="gbm")
        predictor.fit(features)
        metrics = predictor.evaluate()
        logger.info(f"✅ Churn model trained. ROC-AUC: {metrics['roc_auc']:.4f}")
        logger.info(metrics["classification_report"])

    if args.dashboards or args.all:
        logger.info("── Step 5: Generating Dashboards ────────────────────")
        import subprocess
        subprocess.run(["python", "generate_dashboards.py"], check=True)
        logger.info("✅ Dashboards saved to dashboards/")

    if not any(vars(args).values()):
        parser.print_help()


if __name__ == "__main__":
    main()
