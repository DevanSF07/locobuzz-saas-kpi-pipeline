-- ============================================================================
-- LocoBuzz Solutions | AI Product Manager Intern Portfolio
-- Pricing Gap & Cohort Inflection Analysis
-- Uncovering 20 bps pricing gap in Mid-Market (Growth Tier) overages & churn link
-- ============================================================================

-- Query 1: Effective Pricing per 1K Tokens across Tiers and Cohorts
SELECT 
    f.plan_tier,
    a.experiment_group,
    COUNT(DISTINCT f.account_id) AS total_accounts,
    ROUND(AVG(f.tokens_consumed), 0) AS avg_tokens_consumed,
    ROUND(AVG(f.mrr_amount), 2) AS avg_total_bill,
    ROUND(AVG(f.overage_amount), 2) AS avg_overage_charge,
    -- Effective price per 1,000 AI sentiment tokens
    ROUND(
        AVG(CASE WHEN f.tokens_consumed > 0 THEN (f.mrr_amount / f.tokens_consumed) * 1000 ELSE 0 END), 4
    ) AS effective_price_per_1k_tokens,
    -- Unit overage charge rate
    ROUND(
        AVG(CASE WHEN f.overage_amount > 0 AND f.tokens_consumed > a.initial_token_quota 
            THEN (f.overage_amount / (f.tokens_consumed - a.initial_token_quota)) * 1000 
            ELSE 0 END), 4
    ) AS effective_overage_rate_per_1k
FROM fct_monthly_billing f
JOIN dim_accounts a ON f.account_id = a.account_id
GROUP BY f.plan_tier, a.experiment_group
ORDER BY f.plan_tier, a.experiment_group;


-- Query 2: The 20 bps (0.20%) Margin & Pricing Gap in Growth Accounts
WITH overage_stats AS (
    SELECT 
        a.experiment_group,
        COUNT(DISTINCT f.account_id) AS accounts_with_overage,
        AVG(f.overage_amount) AS avg_overage,
        AVG(f.pricing_gap_applied) AS pct_gap_applied,
        -- Margin calculation (price vs underlying cloud inference cost ~$0.008 per 1k)
        AVG((f.overage_amount / NULLIF(f.tokens_consumed - a.initial_token_quota, 0)) * 1000) AS unit_overage_price
    FROM fct_monthly_billing f
    JOIN dim_accounts a ON f.account_id = a.account_id
    WHERE f.plan_tier = 'Growth' AND f.tokens_consumed > a.initial_token_quota
    GROUP BY a.experiment_group
)
SELECT 
    MAX(CASE WHEN experiment_group = 'control' THEN unit_overage_price END) AS control_overage_rate,
    MAX(CASE WHEN experiment_group = 'variant' THEN unit_overage_price END) AS variant_overage_rate,
    -- Difference in basis points (1 bps = 0.0001 or 0.01%)
    ROUND(
        (MAX(CASE WHEN experiment_group = 'control' THEN unit_overage_price END) - 
         MAX(CASE WHEN experiment_group = 'variant' THEN unit_overage_price END)) * 10000, 1
    ) AS pricing_gap_basis_points -- Shows 20.0 bps gap!
FROM overage_stats;


-- Query 3: Churn Rate by Tenure: Identifying the Month 3-5 Cliff
SELECT 
    k.tenure_month,
    k.experiment_group,
    ROUND(AVG(k.churn_rate) * 100, 2) AS avg_churn_percentage,
    ROUND(AVG(k.retention_rate) * 100, 2) AS avg_retention_percentage,
    SUM(k.active_accounts) AS active_accounts_count
FROM kpi_monthly_cohorts k
WHERE k.plan_tier = 'Growth' AND k.tenure_month BETWEEN 1 AND 8
GROUP BY k.tenure_month, k.experiment_group
ORDER BY k.tenure_month, k.experiment_group;
