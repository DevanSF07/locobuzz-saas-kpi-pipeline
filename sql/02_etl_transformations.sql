-- ============================================================================
-- LocoBuzz Solutions | Automated SQL ETL Pipeline Transformations
-- Transforms raw B2B transaction logs and usage logs into structured KPI tables
-- ============================================================================

-- STEP 1: Populate Dimensional Account Table
INSERT INTO dim_accounts (
    account_id,
    company_name,
    industry,
    region,
    plan_tier,
    initial_seats,
    initial_token_quota,
    signup_date,
    cohort_month,
    acquisition_cac,
    experiment_group
)
SELECT 
    account_id,
    company_name,
    industry,
    region,
    plan_tier,
    seats,
    monthly_token_quota,
    signup_date,
    signup_month AS cohort_month,
    cac AS acquisition_cac,
    experiment_group
FROM raw_accounts;


-- STEP 2: Transform Raw Transactions & Usage into Monthly Billing Fact Table
WITH usage_summary AS (
    SELECT 
        account_id,
        log_month,
        SUM(ai_sentiment_tokens) AS tokens_consumed,
        SUM(api_calls_count) AS api_calls_count,
        SUM(tickets_resolved) AS tickets_resolved
    FROM raw_usage_logs
    GROUP BY account_id, log_month
),
monthly_billed AS (
    SELECT 
        t.billing_month,
        t.account_id,
        t.tenure_month,
        t.plan_tier,
        t.total_billed AS mrr_amount,
        t.base_amount,
        t.overage_amount,
        t.discount_amount,
        t.payment_status,
        t.pricing_gap_applied,
        COALESCE(u.tokens_consumed, 0) AS tokens_consumed,
        COALESCE(u.api_calls_count, 0) AS api_calls_count,
        COALESCE(u.tickets_resolved, 0) AS tickets_resolved,
        LAG(t.total_billed, 1, 0.00) OVER (
            PARTITION BY t.account_id 
            ORDER BY t.billing_month
        ) AS previous_mrr
    FROM raw_transactions t
    LEFT JOIN usage_summary u 
        ON t.account_id = u.account_id 
        AND t.billing_month = u.log_month
    WHERE t.payment_status = 'PAID'
)
INSERT INTO fct_monthly_billing (
    billing_month,
    account_id,
    tenure_month,
    plan_tier,
    mrr_amount,
    base_amount,
    overage_amount,
    discount_amount,
    payment_status,
    pricing_gap_applied,
    tokens_consumed,
    api_calls_count,
    tickets_resolved,
    previous_mrr,
    mrr_change,
    revenue_category
)
SELECT 
    billing_month,
    account_id,
    tenure_month,
    plan_tier,
    mrr_amount,
    base_amount,
    overage_amount,
    discount_amount,
    payment_status,
    pricing_gap_applied,
    tokens_consumed,
    api_calls_count,
    tickets_resolved,
    previous_mrr,
    ROUND(mrr_amount - previous_mrr, 2) AS mrr_change,
    CASE 
        WHEN tenure_month = 0 THEN 'NEW'
        WHEN mrr_amount > previous_mrr THEN 'EXPANSION'
        WHEN mrr_amount < previous_mrr THEN 'CONTRACTION'
        ELSE 'RETAINED'
    END AS revenue_category
FROM monthly_billed;


-- STEP 3: Populate KPI Monthly Cohorts Matrix Table
WITH cohort_sizes AS (
    SELECT 
        cohort_month,
        plan_tier,
        experiment_group,
        COUNT(DISTINCT account_id) AS cohort_starting_accounts
    FROM dim_accounts
    GROUP BY cohort_month, plan_tier, experiment_group
),
cohort_activity AS (
    SELECT 
        a.cohort_month,
        f.tenure_month,
        a.plan_tier,
        a.experiment_group,
        COUNT(DISTINCT f.account_id) AS active_accounts,
        SUM(f.mrr_amount) AS total_cohort_mrr,
        ROUND(AVG(f.mrr_amount), 2) AS arpu
    FROM fct_monthly_billing f
    JOIN dim_accounts a ON f.account_id = a.account_id
    GROUP BY a.cohort_month, f.tenure_month, a.plan_tier, a.experiment_group
)
INSERT INTO kpi_monthly_cohorts (
    cohort_month,
    tenure_month,
    plan_tier,
    experiment_group,
    cohort_starting_accounts,
    active_accounts,
    retention_rate,
    churn_rate,
    total_cohort_mrr,
    arpu
)
SELECT 
    ca.cohort_month,
    ca.tenure_month,
    ca.plan_tier,
    ca.experiment_group,
    cs.cohort_starting_accounts,
    ca.active_accounts,
    ROUND(ca.active_accounts::NUMERIC / cs.cohort_starting_accounts, 4) AS retention_rate,
    ROUND(1.0 - (ca.active_accounts::NUMERIC / cs.cohort_starting_accounts), 4) AS churn_rate,
    ca.total_cohort_mrr,
    ca.arpu
FROM cohort_activity ca
JOIN cohort_sizes cs 
    ON ca.cohort_month = cs.cohort_month 
    AND ca.plan_tier = cs.plan_tier 
    AND ca.experiment_group = cs.experiment_group;
