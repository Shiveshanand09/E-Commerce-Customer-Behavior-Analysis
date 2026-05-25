# Data Directory

This directory contains synthetic data for demonstration. In production, replace with your actual data sources.

## Files

| File | Rows | Description |
|------|------|-------------|
| `customers.csv` | ~10,000 | Customer profiles with segments |
| `transactions.csv` | ~100,000 | Order & purchase records |
| `sessions.csv` | ~200,000 | Website session logs |

## Generate Sample Data

```bash
python data/generate_sample_data.py
```

## Schema

### customers.csv
| Column | Type | Description |
|--------|------|-------------|
| customer_id | string | Unique identifier |
| name | string | Full name |
| email | string | Email address |
| city / country | string | Location |
| signup_date | date | Account creation date |
| age | int | Customer age |
| gender | string | Gender |
| segment | string | Premium / Regular / Occasional / At-Risk / Churned |
| lifetime_value | float | Total revenue generated |

### transactions.csv
| Column | Type | Description |
|--------|------|-------------|
| transaction_id | string | Unique transaction ID |
| customer_id | string | FK to customers |
| order_date | date | Purchase date |
| category | string | Product category |
| quantity | int | Units purchased |
| unit_price | float | Price per unit |
| discount_pct | float | Discount applied (%) |
| total_amount | float | Final amount paid |
| payment_method | string | Payment type |
| status | string | Completed / Returned / Cancelled |

### sessions.csv
| Column | Type | Description |
|--------|------|-------------|
| session_id | string | Unique session ID |
| customer_id | string | FK to customers |
| session_date | date | Date of visit |
| device | string | Mobile / Desktop / Tablet |
| traffic_source | string | Acquisition channel |
| pages_viewed | int | Pages in session |
| session_duration_sec | int | Duration in seconds |
| bounced | bool | Single-page visit |
| converted | bool | Resulted in purchase |

> **Note:** All data is synthetically generated using the Faker library. No real customer data is used.
