"""
Sample Data Generator for E-Commerce Customer Behavior Analysis
Generates 100K+ synthetic transaction records for demonstration.
"""

import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import os

fake = Faker()
np.random.seed(42)
random.seed(42)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_customers(n=10000):
    """Generate synthetic customer records."""
    segments = ["Premium", "Regular", "Occasional", "At-Risk", "Churned"]
    seg_weights = [0.10, 0.30, 0.25, 0.20, 0.15]

    customers = []
    for i in range(n):
        signup = fake.date_between(start_date="-3y", end_date="-1m")
        segment = np.random.choice(segments, p=seg_weights)
        customers.append({
            "customer_id": f"CUST{i+1:06d}",
            "name": fake.name(),
            "email": fake.email(),
            "city": fake.city(),
            "country": np.random.choice(["India", "USA", "UK", "Germany", "Australia"],
                                        p=[0.40, 0.30, 0.15, 0.10, 0.05]),
            "signup_date": signup,
            "age": np.random.randint(18, 70),
            "gender": np.random.choice(["Male", "Female", "Other"], p=[0.48, 0.49, 0.03]),
            "segment": segment,
            "lifetime_value": round(np.random.lognormal(5.5, 1.2), 2),
        })
    return pd.DataFrame(customers)


def generate_transactions(customers_df, n=100000):
    """Generate synthetic transaction records linked to customers."""
    categories = ["Electronics", "Clothing", "Home & Kitchen", "Books",
                  "Sports", "Beauty", "Toys", "Grocery", "Automotive"]
    cat_weights = [0.18, 0.22, 0.15, 0.10, 0.08, 0.10, 0.07, 0.06, 0.04]

    payment_methods = ["Credit Card", "Debit Card", "UPI", "Net Banking", "Wallet"]
    status_list = ["Completed", "Returned", "Cancelled"]
    status_weights = [0.85, 0.08, 0.07]

    transactions = []
    customer_ids = customers_df["customer_id"].tolist()

    for i in range(n):
        cust_id = random.choice(customer_ids)
        category = np.random.choice(categories, p=cat_weights)
        order_date = fake.date_between(start_date="-2y", end_date="today")
        qty = np.random.randint(1, 6)
        unit_price = round(np.random.lognormal(4.0, 1.0), 2)
        discount = round(np.random.uniform(0, 0.40), 2)
        amount = round(qty * unit_price * (1 - discount), 2)

        transactions.append({
            "transaction_id": f"TXN{i+1:08d}",
            "customer_id": cust_id,
            "order_date": order_date,
            "category": category,
            "product_name": fake.word().capitalize() + " " + fake.word().capitalize(),
            "quantity": qty,
            "unit_price": unit_price,
            "discount_pct": round(discount * 100, 1),
            "total_amount": amount,
            "payment_method": np.random.choice(payment_methods),
            "status": np.random.choice(status_list, p=status_weights),
            "is_first_purchase": False,
        })

    df = pd.DataFrame(transactions)
    # Mark first purchases
    df = df.sort_values("order_date")
    first_purchases = df.groupby("customer_id").head(1).index
    df.loc[first_purchases, "is_first_purchase"] = True
    return df.reset_index(drop=True)


def generate_sessions(customers_df, n=200000):
    """Generate website session data."""
    devices = ["Mobile", "Desktop", "Tablet"]
    device_weights = [0.55, 0.35, 0.10]
    sources = ["Organic Search", "Paid Search", "Social Media", "Email", "Direct", "Referral"]
    source_weights = [0.28, 0.22, 0.20, 0.15, 0.10, 0.05]

    sessions = []
    customer_ids = customers_df["customer_id"].tolist()

    for i in range(n):
        cust_id = random.choice(customer_ids)
        session_date = fake.date_between(start_date="-2y", end_date="today")
        duration = max(10, int(np.random.exponential(300)))
        pages = max(1, int(np.random.exponential(4)))

        sessions.append({
            "session_id": f"SES{i+1:09d}",
            "customer_id": cust_id,
            "session_date": session_date,
            "device": np.random.choice(devices, p=device_weights),
            "traffic_source": np.random.choice(sources, p=source_weights),
            "pages_viewed": pages,
            "session_duration_sec": duration,
            "bounced": pages == 1,
            "converted": np.random.random() < 0.08,
        })

    return pd.DataFrame(sessions)


if __name__ == "__main__":
    print("🔄 Generating customer records...")
    customers = generate_customers(10000)
    customers.to_csv(os.path.join(OUTPUT_DIR, "customers.csv"), index=False)
    print(f"   ✅ {len(customers):,} customers saved.")

    print("🔄 Generating transaction records...")
    transactions = generate_transactions(customers, 100000)
    transactions.to_csv(os.path.join(OUTPUT_DIR, "transactions.csv"), index=False)
    print(f"   ✅ {len(transactions):,} transactions saved.")

    print("🔄 Generating session data...")
    sessions = generate_sessions(customers, 200000)
    sessions.to_csv(os.path.join(OUTPUT_DIR, "sessions.csv"), index=False)
    print(f"   ✅ {len(sessions):,} sessions saved.")

    print("\n✅ All sample data generated successfully in /data/")
