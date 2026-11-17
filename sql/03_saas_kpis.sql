-- ============================================================================
-- LocoBuzz Solutions | SaaS Executive KPI SQL Feed
-- Calculates core SaaS metrics: MRR, Logo Churn, Revenue Churn, CAC, LTV, NRR
-- ============================================================================

WITH monthly_totals AS (
    SELECT 
        billing_month,
        COUNT(DISTINCT account_id) AS total_active_accounts,
        SUM(mrr_amount) AS ending_mrr,
        SUM(CASE WHEN revenue_category = 'NEW' THEN mrr_amount ELSE 0 END) AS new_mrr,
        SUM(CASE WHEN revenue_category = 'EXPANSION' THEN mrr_change ELSE 0 END) AS expansion_mrr,
        SUM(CASE WHEN revenue_category = 'CONTRACTION' THEN ABS(mrr_change) ELSE 0 END) AS contraction_mrr
    FROM fct_monthly_billing
    GROUP BY billing_month
),
churn_metrics AS (
    -- Accounts that were active in month M-1 but not present in month M
    SELECT 
        curr.billing_month,
        COUNT(DISTINCT prev.account_id) AS churned_accounts,
        COALESCE(SUM(prev.mrr_amount), 0) AS churned_mrr
    FROM fct_monthly_billing prev
    JOIN (
        SELECT DISTINCT billing_month FROM fct_monthly_billing
    ) curr ON curr.billing_month = TO_CHAR(TO_DATE(prev.billing_month, 'YYYY-MM') + INTERVAL '1 month', 'YYYY-MM')
    WHERE prev.account_id NOT IN (
        SELECT account_id FROM fct_monthly_billing WHERE billing_month = curr.billing_month
    )
    GROUP BY curr.billing_month
),
unit_economics AS (
    SELECT 
        f.billing_month,
        ROUND(AVG(a.acquisition_cac), 2) AS avg_cac,
        ROUND(AVG(f.mrr_amount), 2) AS arpu
    FROM fct_monthly_billing f
    JOIN dim_accounts a ON f.account_id = a.account_id
    GROUP BY f.billing_month
)
INSERT INTO agg_executive_saas_kpis (
    billing_month,
    total_active_accounts,
    ending_mrr,
    new_mrr,
    expansion_mrr,
    contraction_mrr,
    churned_mrr,
    net_mrr_growth,
    net_revenue_retention_rate,
    gross_revenue_churn_rate,
    logo_churn_rate,
    avg_cac,
    avg_ltv,
    ltv_to_cac_ratio,
    saas_quick_ratio
)
SELECT 
    m.billing_month,
    m.total_active_accounts,
    m.ending_mrr,
    m.new_mrr,
    m.expansion_mrr,
    m.contraction_mrr,
    COALESCE(c.churned_mrr, 0) AS churned_mrr,
    ROUND(m.new_mrr + m.expansion_mrr - m.contraction_mrr - COALESCE(c.churned_mrr, 0), 2) AS net_mrr_growth,
    -- Net Revenue Retention %: (Ending MRR from existing accounts) / (Starting MRR)
    ROUND(
        CASE 
            WHEN LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month) > 0 
            THEN ((LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month) + m.expansion_mrr - m.contraction_mrr - COALESCE(c.churned_mrr, 0))::NUMERIC 
                  / LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month)) * 100
            ELSE 100.00 
        END, 2
    ) AS net_revenue_retention_rate,
    -- Gross Revenue Churn Rate %
    ROUND(
        CASE 
            WHEN LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month) > 0 
            THEN (COALESCE(c.churned_mrr, 0)::NUMERIC / LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month))
            ELSE 0.0000 
        END, 4
    ) AS gross_revenue_churn_rate,
    -- Logo Churn Rate %
    ROUND(
        CASE 
            WHEN LAG(m.total_active_accounts, 1) OVER (ORDER BY m.billing_month) > 0 
            THEN (COALESCE(c.churned_accounts, 0)::NUMERIC / LAG(m.total_active_accounts, 1) OVER (ORDER BY m.billing_month))
            ELSE 0.0000 
        END, 4
    ) AS logo_churn_rate,
    u.avg_cac,
    -- LTV = ARPU / Gross Revenue Churn Rate
    ROUND(
        CASE 
            WHEN COALESCE(c.churned_mrr, 0) > 0 AND LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month) > 0 
            THEN (u.arpu / (c.churned_mrr::NUMERIC / LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month)))
            ELSE u.arpu * 24.0 -- default 24 months cap
        END, 2
    ) AS avg_ltv,
    -- LTV to CAC Ratio
    ROUND(
        CASE 
            WHEN u.avg_cac > 0 AND COALESCE(c.churned_mrr, 0) > 0 AND LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month) > 0
            THEN (u.arpu / (c.churned_mrr::NUMERIC / LAG(m.ending_mrr, 1) OVER (ORDER BY m.billing_month))) / u.avg_cac
            ELSE 3.50
        END, 2
    ) AS ltv_to_cac_ratio,
    -- SaaS Quick Ratio: (New MRR + Expansion MRR) / (Contraction MRR + Churned MRR)
    ROUND(
        CASE 
            WHEN (m.contraction_mrr + COALESCE(c.churned_mrr, 0)) > 0 
            THEN (m.new_mrr + m.expansion_mrr) / (m.contraction_mrr + COALESCE(c.churned_mrr, 0))
            ELSE 4.00 
        END, 2
    ) AS saas_quick_ratio
FROM monthly_totals m
LEFT JOIN churn_metrics c ON m.billing_month = c.billing_month
JOIN unit_economics u ON m.billing_month = u.billing_month
ORDER BY m.billing_month;
