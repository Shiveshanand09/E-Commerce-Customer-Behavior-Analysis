-- ============================================================
-- Customer Segmentation Queries
-- E-Commerce Customer Behavior Analysis
-- ============================================================

-- ──────────────────────────────────────────────
-- 1. RFM Segmentation (Recency, Frequency, Monetary)
-- ──────────────────────────────────────────────
WITH rfm_base AS (
    SELECT
        customer_id,
        DATEDIFF(CURRENT_DATE, MAX(order_date))       AS recency_days,
        COUNT(DISTINCT transaction_id)                 AS frequency,
        ROUND(SUM(total_amount), 2)                    AS monetary
    FROM transactions
    WHERE status = 'Completed'
    GROUP BY customer_id
),
rfm_scores AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days DESC)    AS r_score,   -- lower recency = better
        NTILE(5) OVER (ORDER BY frequency ASC)         AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)          AS m_score
    FROM rfm_base
),
rfm_segments AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        CONCAT(r_score, f_score, m_score)              AS rfm_code,
        ROUND((r_score + f_score + m_score) / 3.0, 2) AS rfm_avg,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2                   THEN 'New Customers'
            WHEN r_score >= 3 AND f_score >= 1 AND m_score >= 2  THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4  THEN 'At Risk'
            WHEN r_score <= 2 AND f_score >= 2 AND m_score >= 2  THEN 'Needs Attention'
            WHEN r_score = 1 AND f_score = 1                     THEN 'Lost'
            ELSE 'Hibernating'
        END AS rfm_segment
    FROM rfm_scores
)
SELECT
    rfm_segment,
    COUNT(*)                           AS customer_count,
    ROUND(AVG(recency_days), 1)        AS avg_recency_days,
    ROUND(AVG(frequency), 1)           AS avg_orders,
    ROUND(AVG(monetary), 2)            AS avg_revenue,
    ROUND(SUM(monetary), 2)            AS total_revenue
FROM rfm_segments
GROUP BY rfm_segment
ORDER BY total_revenue DESC;


-- ──────────────────────────────────────────────
-- 2. Customer Lifetime Value by Segment
-- ──────────────────────────────────────────────
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id)                          AS customers,
    ROUND(AVG(c.lifetime_value), 2)                        AS avg_ltv,
    ROUND(SUM(c.lifetime_value), 2)                        AS total_ltv,
    ROUND(AVG(DATEDIFF(CURRENT_DATE, c.signup_date)), 0)   AS avg_tenure_days,
    ROUND(AVG(t.order_count), 1)                           AS avg_orders
FROM customers c
LEFT JOIN (
    SELECT customer_id, COUNT(*) AS order_count
    FROM transactions
    WHERE status = 'Completed'
    GROUP BY customer_id
) t ON c.customer_id = t.customer_id
GROUP BY c.segment
ORDER BY avg_ltv DESC;


-- ──────────────────────────────────────────────
-- 3. Top Revenue-Contributing Customers (Pareto)
-- ──────────────────────────────────────────────
WITH customer_revenue AS (
    SELECT
        t.customer_id,
        c.segment,
        ROUND(SUM(t.total_amount), 2) AS revenue
    FROM transactions t
    JOIN customers c ON t.customer_id = c.customer_id
    WHERE t.status = 'Completed'
    GROUP BY t.customer_id, c.segment
),
ranked AS (
    SELECT
        customer_id,
        segment,
        revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rank_num,
        SUM(revenue) OVER ()                       AS total_revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC)  AS cumulative_revenue
    FROM customer_revenue
)
SELECT
    customer_id,
    segment,
    revenue,
    rank_num,
    ROUND(100.0 * revenue / total_revenue, 3)            AS pct_of_total,
    ROUND(100.0 * cumulative_revenue / total_revenue, 2) AS cumulative_pct
FROM ranked
WHERE rank_num <= 2000   -- Top 20% of ~10K customers
ORDER BY rank_num;


-- ──────────────────────────────────────────────
-- 4. Segment Migration (Month-over-Month)
-- ──────────────────────────────────────────────
WITH monthly_spend AS (
    SELECT
        customer_id,
        DATE_FORMAT(order_date, '%Y-%m') AS month,
        SUM(total_amount)                AS spend
    FROM transactions
    WHERE status = 'Completed'
    GROUP BY customer_id, DATE_FORMAT(order_date, '%Y-%m')
),
segmented AS (
    SELECT
        customer_id,
        month,
        spend,
        CASE
            WHEN spend >= 5000  THEN 'High Value'
            WHEN spend >= 1000  THEN 'Mid Value'
            WHEN spend >= 100   THEN 'Low Value'
            ELSE 'Minimal'
        END AS spend_segment
    FROM monthly_spend
)
SELECT
    month,
    spend_segment,
    COUNT(DISTINCT customer_id) AS customer_count,
    ROUND(SUM(spend), 2)        AS total_spend
FROM segmented
GROUP BY month, spend_segment
ORDER BY month, spend_segment;
