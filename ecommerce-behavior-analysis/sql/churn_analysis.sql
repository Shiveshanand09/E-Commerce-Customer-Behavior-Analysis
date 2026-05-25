-- ============================================================
-- Churn Analysis Queries
-- E-Commerce Customer Behavior Analysis
-- ============================================================

-- ──────────────────────────────────────────────
-- 1. Identify Churned Customers (no purchase in 90+ days)
-- ──────────────────────────────────────────────
WITH last_purchase AS (
    SELECT
        customer_id,
        MAX(order_date)                              AS last_order_date,
        DATEDIFF(CURRENT_DATE, MAX(order_date))      AS days_since_purchase,
        COUNT(DISTINCT transaction_id)               AS total_orders,
        ROUND(SUM(total_amount), 2)                  AS total_spent
    FROM transactions
    WHERE status = 'Completed'
    GROUP BY customer_id
),
churn_status AS (
    SELECT
        lp.customer_id,
        c.segment,
        lp.last_order_date,
        lp.days_since_purchase,
        lp.total_orders,
        lp.total_spent,
        CASE
            WHEN lp.days_since_purchase > 180  THEN 'Churned'
            WHEN lp.days_since_purchase > 90   THEN 'At Risk'
            WHEN lp.days_since_purchase > 30   THEN 'Cooling Off'
            ELSE 'Active'
        END AS churn_label
    FROM last_purchase lp
    JOIN customers c ON lp.customer_id = c.customer_id
)
SELECT
    churn_label,
    COUNT(*)                    AS customer_count,
    ROUND(AVG(total_orders), 1) AS avg_orders,
    ROUND(AVG(total_spent), 2)  AS avg_spent,
    ROUND(SUM(total_spent), 2)  AS at_risk_revenue
FROM churn_status
GROUP BY churn_label
ORDER BY FIELD(churn_label, 'Active', 'Cooling Off', 'At Risk', 'Churned');


-- ──────────────────────────────────────────────
-- 2. Churn Rate by Cohort Month
-- ──────────────────────────────────────────────
WITH cohorts AS (
    SELECT
        customer_id,
        DATE_FORMAT(signup_date, '%Y-%m') AS cohort_month
    FROM customers
),
orders AS (
    SELECT
        customer_id,
        DATE_FORMAT(order_date, '%Y-%m') AS order_month
    FROM transactions
    WHERE status = 'Completed'
),
cohort_orders AS (
    SELECT
        c.cohort_month,
        o.order_month,
        COUNT(DISTINCT o.customer_id) AS active_customers
    FROM cohorts c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.cohort_month, o.order_month
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS total_customers
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    co.cohort_month,
    cs.total_customers,
    co.order_month,
    PERIOD_DIFF(
        REPLACE(co.order_month, '-', ''),
        REPLACE(co.cohort_month, '-', '')
    )                                                                  AS months_since_join,
    co.active_customers,
    ROUND(100.0 * co.active_customers / cs.total_customers, 2)        AS retention_rate,
    ROUND(100.0 * (1 - co.active_customers / cs.total_customers), 2)  AS churn_rate
FROM cohort_orders co
JOIN cohort_size cs ON co.cohort_month = cs.cohort_month
ORDER BY co.cohort_month, months_since_join;


-- ──────────────────────────────────────────────
-- 3. Churn Signals — Behavioral Indicators
-- ──────────────────────────────────────────────
WITH signals AS (
    SELECT
        t.customer_id,
        c.segment,
        COUNT(DISTINCT t.transaction_id)          AS total_txns,
        ROUND(AVG(t.total_amount), 2)              AS avg_order_value,
        ROUND(SUM(t.total_amount), 2)              AS total_revenue,
        SUM(CASE WHEN t.status = 'Returned'   THEN 1 ELSE 0 END)   AS returns,
        SUM(CASE WHEN t.status = 'Cancelled'  THEN 1 ELSE 0 END)   AS cancellations,
        DATEDIFF(CURRENT_DATE, MAX(t.order_date)) AS days_since_last_order,
        s.avg_session_duration,
        s.avg_pages_viewed,
        s.bounce_rate
    FROM transactions t
    JOIN customers c ON t.customer_id = c.customer_id
    LEFT JOIN (
        SELECT
            customer_id,
            ROUND(AVG(session_duration_sec), 0) AS avg_session_duration,
            ROUND(AVG(pages_viewed), 1)          AS avg_pages_viewed,
            ROUND(AVG(bounced) * 100, 1)         AS bounce_rate
        FROM sessions
        GROUP BY customer_id
    ) s ON t.customer_id = s.customer_id
    GROUP BY t.customer_id, c.segment, s.avg_session_duration, s.avg_pages_viewed, s.bounce_rate
)
SELECT
    customer_id,
    segment,
    total_txns,
    avg_order_value,
    total_revenue,
    returns,
    cancellations,
    days_since_last_order,
    avg_session_duration,
    bounce_rate,
    CASE
        WHEN days_since_last_order > 90 AND returns > 2              THEN 'High Churn Risk'
        WHEN days_since_last_order > 60 AND cancellations > 1        THEN 'Medium Churn Risk'
        WHEN days_since_last_order > 30 AND bounce_rate > 70         THEN 'Medium Churn Risk'
        ELSE 'Low Churn Risk'
    END AS churn_risk_level
FROM signals
ORDER BY days_since_last_order DESC;


-- ──────────────────────────────────────────────
-- 4. Revenue at Risk from Churn
-- ──────────────────────────────────────────────
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id)                 AS churned_customers,
    ROUND(AVG(c.lifetime_value), 2)               AS avg_ltv,
    ROUND(SUM(c.lifetime_value), 2)               AS total_revenue_at_risk,
    ROUND(AVG(DATEDIFF(CURRENT_DATE, c.signup_date)) / 365.0, 1) AS avg_tenure_years
FROM customers c
WHERE c.segment = 'Churned'
   OR c.customer_id IN (
       SELECT customer_id
       FROM transactions
       WHERE status = 'Completed'
       GROUP BY customer_id
       HAVING DATEDIFF(CURRENT_DATE, MAX(order_date)) > 90
   )
GROUP BY c.segment
ORDER BY total_revenue_at_risk DESC;
