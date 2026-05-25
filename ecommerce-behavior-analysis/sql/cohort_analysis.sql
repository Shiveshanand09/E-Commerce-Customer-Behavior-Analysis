-- ============================================================
-- Cohort Analysis Queries
-- E-Commerce Customer Behavior Analysis
-- ============================================================

-- ──────────────────────────────────────────────
-- 1. Monthly Cohort Retention Matrix
-- ──────────────────────────────────────────────
WITH first_purchase AS (
    SELECT
        customer_id,
        DATE_FORMAT(MIN(order_date), '%Y-%m') AS cohort_month
    FROM transactions
    WHERE status = 'Completed'
    GROUP BY customer_id
),
activity AS (
    SELECT
        t.customer_id,
        DATE_FORMAT(t.order_date, '%Y-%m') AS activity_month
    FROM transactions t
    WHERE t.status = 'Completed'
    GROUP BY t.customer_id, DATE_FORMAT(t.order_date, '%Y-%m')
),
cohort_matrix AS (
    SELECT
        fp.cohort_month,
        PERIOD_DIFF(
            CAST(REPLACE(a.activity_month, '-', '') AS UNSIGNED),
            CAST(REPLACE(fp.cohort_month,  '-', '') AS UNSIGNED)
        )                                 AS month_number,
        COUNT(DISTINCT a.customer_id)     AS active_users
    FROM first_purchase fp
    JOIN activity a ON fp.customer_id = a.customer_id
    GROUP BY fp.cohort_month, month_number
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM first_purchase
    GROUP BY cohort_month
)
SELECT
    cm.cohort_month,
    cs.cohort_size,
    cm.month_number,
    cm.active_users,
    ROUND(100.0 * cm.active_users / cs.cohort_size, 2) AS retention_pct
FROM cohort_matrix cm
JOIN cohort_sizes cs ON cm.cohort_month = cs.cohort_month
WHERE cm.month_number BETWEEN 0 AND 11
ORDER BY cm.cohort_month, cm.month_number;


-- ──────────────────────────────────────────────
-- 2. Average Order Value by Cohort & Month
-- ──────────────────────────────────────────────
WITH first_purchase AS (
    SELECT
        customer_id,
        DATE_FORMAT(MIN(order_date), '%Y-%m') AS cohort_month
    FROM transactions
    WHERE status = 'Completed'
    GROUP BY customer_id
)
SELECT
    fp.cohort_month,
    DATE_FORMAT(t.order_date, '%Y-%m')             AS activity_month,
    PERIOD_DIFF(
        CAST(REPLACE(DATE_FORMAT(t.order_date, '%Y-%m'), '-', '') AS UNSIGNED),
        CAST(REPLACE(fp.cohort_month, '-', '') AS UNSIGNED)
    )                                              AS month_number,
    COUNT(DISTINCT t.transaction_id)               AS total_orders,
    ROUND(AVG(t.total_amount), 2)                  AS avg_order_value,
    ROUND(SUM(t.total_amount), 2)                  AS total_revenue
FROM transactions t
JOIN first_purchase fp ON t.customer_id = fp.customer_id
WHERE t.status = 'Completed'
GROUP BY fp.cohort_month, activity_month, month_number
ORDER BY fp.cohort_month, month_number;


-- ──────────────────────────────────────────────
-- 3. Category Purchase Progression by Cohort
-- ──────────────────────────────────────────────
WITH first_purchase AS (
    SELECT
        customer_id,
        DATE_FORMAT(MIN(order_date), '%Y-%m') AS cohort_month
    FROM transactions
    WHERE status = 'Completed'
    GROUP BY customer_id
)
SELECT
    fp.cohort_month,
    t.category,
    PERIOD_DIFF(
        CAST(REPLACE(DATE_FORMAT(t.order_date, '%Y-%m'), '-', '') AS UNSIGNED),
        CAST(REPLACE(fp.cohort_month, '-', '') AS UNSIGNED)
    )                                          AS months_since_join,
    COUNT(DISTINCT t.customer_id)              AS buyers,
    ROUND(SUM(t.total_amount), 2)              AS revenue
FROM transactions t
JOIN first_purchase fp ON t.customer_id = fp.customer_id
WHERE t.status = 'Completed'
GROUP BY fp.cohort_month, t.category, months_since_join
ORDER BY fp.cohort_month, months_since_join, revenue DESC;


-- ──────────────────────────────────────────────
-- 4. Cumulative Revenue by Cohort (LTV Curve)
-- ──────────────────────────────────────────────
WITH first_purchase AS (
    SELECT
        customer_id,
        DATE_FORMAT(MIN(order_date), '%Y-%m') AS cohort_month
    FROM transactions WHERE status = 'Completed'
    GROUP BY customer_id
),
monthly_revenue AS (
    SELECT
        fp.cohort_month,
        PERIOD_DIFF(
            CAST(REPLACE(DATE_FORMAT(t.order_date, '%Y-%m'), '-', '') AS UNSIGNED),
            CAST(REPLACE(fp.cohort_month, '-', '') AS UNSIGNED)
        )                           AS month_number,
        SUM(t.total_amount)         AS revenue
    FROM transactions t
    JOIN first_purchase fp ON t.customer_id = fp.customer_id
    WHERE t.status = 'Completed'
    GROUP BY fp.cohort_month, month_number
)
SELECT
    cohort_month,
    month_number,
    ROUND(revenue, 2)                                          AS monthly_revenue,
    ROUND(SUM(revenue) OVER (
        PARTITION BY cohort_month
        ORDER BY month_number
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2)                                                      AS cumulative_revenue
FROM monthly_revenue
ORDER BY cohort_month, month_number;
