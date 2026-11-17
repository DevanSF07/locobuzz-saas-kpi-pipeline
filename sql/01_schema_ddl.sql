-- ============================================================================
-- LocoBuzz Solutions | AI Product Manager Intern Portfolio
-- Database DDL: Postgres Schemas for B2B SaaS Customer Analytics & Cohorts
-- Scale: 17K+ B2B Client Accounts, Monthly Billing Transactions & Product Logs
-- ============================================================================

-- Drop existing tables for fresh build
DROP TABLE IF EXISTS agg_executive_saas_kpis CASCADE;
DROP TABLE IF EXISTS kpi_monthly_cohorts CASCADE;
DROP TABLE IF EXISTS fct_monthly_billing CASCADE;
DROP TABLE IF EXISTS dim_accounts CASCADE;
DROP TABLE IF EXISTS raw_usage_logs CASCADE;
DROP TABLE IF EXISTS raw_transactions CASCADE;
DROP TABLE IF EXISTS raw_accounts CASCADE;

-- 1. Raw Ingestion Layer
CREATE TABLE raw_accounts (
    account_id VARCHAR(32) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    region VARCHAR(100),
    plan_tier VARCHAR(50) NOT NULL,
    seats INTEGER NOT NULL,
    monthly_token_quota BIGINT NOT NULL,
    signup_date DATE NOT NULL,
    signup_month VARCHAR(7) NOT NULL,
    cac NUMERIC(10, 2) NOT NULL,
    experiment_group VARCHAR(20) DEFAULT 'control'
);

CREATE TABLE raw_transactions (
    txn_id VARCHAR(32) PRIMARY KEY,
    account_id VARCHAR(32) NOT NULL REFERENCES raw_accounts(account_id),
    billing_date DATE NOT NULL,
    billing_month VARCHAR(7) NOT NULL,
    tenure_month INTEGER NOT NULL,
    plan_tier VARCHAR(50) NOT NULL,
    base_amount NUMERIC(10, 2) NOT NULL,
    overage_amount NUMERIC(10, 2) DEFAULT 0.00,
    discount_amount NUMERIC(10, 2) DEFAULT 0.00,
    total_billed NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    payment_status VARCHAR(20) NOT NULL,
    pricing_gap_applied INTEGER DEFAULT 0
);

CREATE TABLE raw_usage_logs (
    log_id VARCHAR(32) PRIMARY KEY,
    account_id VARCHAR(32) NOT NULL REFERENCES raw_accounts(account_id),
    log_month VARCHAR(7) NOT NULL,
    ai_sentiment_tokens BIGINT NOT NULL,
    tickets_resolved INTEGER NOT NULL,
    active_agent_seats INTEGER NOT NULL,
    api_calls_count INTEGER NOT NULL
);

-- 2. Dimensional Data Modeling Layer
CREATE TABLE dim_accounts (
    account_id VARCHAR(32) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    region VARCHAR(100),
    plan_tier VARCHAR(50) NOT NULL,
    initial_seats INTEGER NOT NULL,
    initial_token_quota BIGINT NOT NULL,
    signup_date DATE NOT NULL,
    cohort_month VARCHAR(7) NOT NULL,
    acquisition_cac NUMERIC(10, 2) NOT NULL,
    experiment_group VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fct_monthly_billing (
    billing_month VARCHAR(7) NOT NULL,
    account_id VARCHAR(32) NOT NULL REFERENCES dim_accounts(account_id),
    tenure_month INTEGER NOT NULL,
    plan_tier VARCHAR(50) NOT NULL,
    mrr_amount NUMERIC(10, 2) NOT NULL,
    base_amount NUMERIC(10, 2) NOT NULL,
    overage_amount NUMERIC(10, 2) NOT NULL,
    discount_amount NUMERIC(10, 2) NOT NULL,
    payment_status VARCHAR(20) NOT NULL,
    pricing_gap_applied INTEGER NOT NULL,
    tokens_consumed BIGINT,
    api_calls_count INTEGER,
    tickets_resolved INTEGER,
    previous_mrr NUMERIC(10, 2) DEFAULT 0.00,
    mrr_change NUMERIC(10, 2) DEFAULT 0.00,
    revenue_category VARCHAR(30), -- 'NEW', 'EXPANSION', 'CONTRACTION', 'RETAINED', 'CHURNED'
    PRIMARY KEY (billing_month, account_id)
);

-- 3. Aggregated Reporting & Tableau Feed Layer
CREATE TABLE kpi_monthly_cohorts (
    cohort_month VARCHAR(7) NOT NULL,
    tenure_month INTEGER NOT NULL,
    plan_tier VARCHAR(50) NOT NULL,
    experiment_group VARCHAR(20) NOT NULL,
    cohort_starting_accounts INTEGER NOT NULL,
    active_accounts INTEGER NOT NULL,
    retention_rate NUMERIC(6, 4) NOT NULL,
    churn_rate NUMERIC(6, 4) NOT NULL,
    total_cohort_mrr NUMERIC(12, 2) NOT NULL,
    arpu NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (cohort_month, tenure_month, plan_tier, experiment_group)
);

CREATE TABLE agg_executive_saas_kpis (
    billing_month VARCHAR(7) PRIMARY KEY,
    total_active_accounts INTEGER NOT NULL,
    ending_mrr NUMERIC(14, 2) NOT NULL,
    new_mrr NUMERIC(14, 2) NOT NULL,
    expansion_mrr NUMERIC(14, 2) NOT NULL,
    contraction_mrr NUMERIC(14, 2) NOT NULL,
    churned_mrr NUMERIC(14, 2) NOT NULL,
    net_mrr_growth NUMERIC(14, 2) NOT NULL,
    net_revenue_retention_rate NUMERIC(6, 2) NOT NULL, -- NRR %
    gross_revenue_churn_rate NUMERIC(6, 4) NOT NULL,
    logo_churn_rate NUMERIC(6, 4) NOT NULL,
    avg_cac NUMERIC(10, 2) NOT NULL,
    avg_ltv NUMERIC(12, 2) NOT NULL,
    ltv_to_cac_ratio NUMERIC(6, 2) NOT NULL,
    saas_quick_ratio NUMERIC(6, 2) NOT NULL
);

-- Performance Indexes
CREATE INDEX idx_dim_accounts_cohort ON dim_accounts(cohort_month);
CREATE INDEX idx_dim_accounts_plan ON dim_accounts(plan_tier);
CREATE INDEX idx_fct_billing_account ON fct_monthly_billing(account_id);
CREATE INDEX idx_fct_billing_month ON fct_monthly_billing(billing_month);
CREATE INDEX idx_cohorts_lookup ON kpi_monthly_cohorts(cohort_month, tenure_month);
