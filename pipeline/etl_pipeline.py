#!/usr/bin/env python3
"""
LocoBuzz Solutions | Automated SQL ETL Pipeline Engine
Ingests 17K+ raw B2B transaction logs, builds dimensional models,
computes KPI cohort tables, and exports executive Tableau feeds.
"""

import os
import sys
import time
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
TABLEAU_DIR = os.path.join(BASE_DIR, "dashboard", "tableau_feeds")
DB_PATH = os.path.join(PROCESSED_DIR, "locobuzz_analytics.db")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(TABLEAU_DIR, exist_ok=True)

def log(step, msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{step}] {msg}")

def run_etl():
    start_time = time.time()
    log("INIT", "Starting LocoBuzz Automated SQL ETL Pipeline...")

    # 1. Verify Raw Input Files
    acc_file = os.path.join(RAW_DIR, "raw_accounts.csv")
    txn_file = os.path.join(RAW_DIR, "raw_transactions.csv")
    use_file = os.path.join(RAW_DIR, "raw_usage_logs.csv")

    for f in [acc_file, txn_file, use_file]:
        if not os.path.exists(f):
            log("ERROR", f"Missing raw data file: {f}. Run generate_synthetic_data.py first.")
            sys.exit(1)

    # 2. Ingest into SQL Database Engine
    log("INGEST", f"Loading raw CSVs into analytical engine (Database: {DB_PATH})...")
    conn = sqlite3.connect(DB_PATH)
    
    df_accounts = pd.read_csv(acc_file)
    df_txns = pd.read_csv(txn_file)
    df_usage = pd.read_csv(use_file)

    df_accounts.to_sql("raw_accounts", conn, if_exists="replace", index=False)
    df_txns.to_sql("raw_transactions", conn, if_exists="replace", index=False)
    df_usage.to_sql("raw_usage_logs", conn, if_exists="replace", index=False)
    log("INGEST", f"Successfully staged {len(df_accounts):,} accounts, {len(df_txns):,} transactions, {len(df_usage):,} usage records.")

    # 3. Build Dimensional & Fact Tables
    log("TRANSFORM", "Building dimensional models (dim_accounts & fct_monthly_billing)...")
    
    # Create dim_accounts
    conn.execute("DROP TABLE IF EXISTS dim_accounts;")
    conn.execute("""
        CREATE TABLE dim_accounts AS
        SELECT 
            account_id,
            company_name,
            industry,
            region,
            plan_tier,
            seats AS initial_seats,
            monthly_token_quota AS initial_token_quota,
            signup_date,
            signup_month AS cohort_month,
            cac AS acquisition_cac,
            experiment_group
        FROM raw_accounts;
    """)

    # Create fct_monthly_billing with window function
    conn.execute("DROP TABLE IF EXISTS fct_monthly_billing;")
    conn.execute("""
        CREATE TABLE fct_monthly_billing AS
        WITH usage_agg AS (
            SELECT 
                account_id,
                log_month,
                SUM(ai_sentiment_tokens) AS tokens_consumed,
                SUM(api_calls_count) AS api_calls_count,
                SUM(tickets_resolved) AS tickets_resolved
            FROM raw_usage_logs
            GROUP BY account_id, log_month
        ),
        billed_enriched AS (
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
                LAG(t.total_billed, 1, 0.0) OVER (
                    PARTITION BY t.account_id 
                    ORDER BY t.billing_month
                ) AS previous_mrr
            FROM raw_transactions t
            LEFT JOIN usage_agg u 
                ON t.account_id = u.account_id 
                AND t.billing_month = u.log_month
            WHERE t.payment_status = 'PAID'
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
        FROM billed_enriched;
    """)

    # 4. Build KPI Monthly Cohorts Matrix
    log("TRANSFORM", "Aggregating monthly retention & churn cohort tables...")
    conn.execute("DROP TABLE IF EXISTS kpi_monthly_cohorts;")
    conn.execute("""
        CREATE TABLE kpi_monthly_cohorts AS
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
        SELECT 
            ca.cohort_month,
            ca.tenure_month,
            ca.plan_tier,
            ca.experiment_group,
            cs.cohort_starting_accounts,
            ca.active_accounts,
            ROUND(CAST(ca.active_accounts AS FLOAT) / cs.cohort_starting_accounts, 4) AS retention_rate,
            ROUND(1.0 - (CAST(ca.active_accounts AS FLOAT) / cs.cohort_starting_accounts), 4) AS churn_rate,
            ca.total_cohort_mrr,
            ca.arpu
        FROM cohort_activity ca
        JOIN cohort_sizes cs 
            ON ca.cohort_month = cs.cohort_month 
            AND ca.plan_tier = cs.plan_tier 
            AND ca.experiment_group = cs.experiment_group;
    """)

    # 5. Build Executive SaaS KPI Summary
    log("TRANSFORM", "Computing Executive SaaS KPIs (MRR Waterfall, Churn, LTV, CAC, NRR, Quick Ratio)...")
    conn.execute("DROP TABLE IF EXISTS agg_executive_saas_kpis;")
    
    # Compute via SQL and pandas for clean interval/churn calculations
    query_monthly = """
        SELECT 
            f.billing_month,
            COUNT(DISTINCT f.account_id) AS active_accounts,
            SUM(f.mrr_amount) AS total_mrr,
            SUM(CASE WHEN f.revenue_category = 'NEW' THEN f.mrr_amount ELSE 0 END) AS new_mrr,
            SUM(CASE WHEN f.revenue_category = 'EXPANSION' THEN f.mrr_change ELSE 0 END) AS expansion_mrr,
            SUM(CASE WHEN f.revenue_category = 'CONTRACTION' THEN ABS(f.mrr_change) ELSE 0 END) AS contraction_mrr,
            AVG(a.acquisition_cac) AS avg_cac,
            AVG(f.mrr_amount) AS arpu
        FROM fct_monthly_billing f
        JOIN dim_accounts a ON f.account_id = a.account_id
        GROUP BY f.billing_month
        ORDER BY f.billing_month;
    """
    df_monthly = pd.read_sql_query(query_monthly, conn)
    
    # Calculate churn by looking at account transitions
    df_fct = pd.read_sql_query("SELECT billing_month, account_id, mrr_amount FROM fct_monthly_billing", conn)
    months = sorted(df_fct["billing_month"].unique())
    
    churn_data = []
    for i in range(1, len(months)):
        prev_m = months[i-1]
        curr_m = months[i]
        prev_accs = set(df_fct[df_fct["billing_month"] == prev_m]["account_id"])
        curr_accs = set(df_fct[df_fct["billing_month"] == curr_m]["account_id"])
        
        churned = prev_accs - curr_accs
        churned_mrr = df_fct[(df_fct["billing_month"] == prev_m) & (df_fct["account_id"].isin(churned))]["mrr_amount"].sum()
        churn_data.append({
            "billing_month": curr_m,
            "churned_accounts": len(churned),
            "churned_mrr": churned_mrr
        })
    
    df_churn = pd.DataFrame(churn_data)
    df_kpi = pd.merge(df_monthly, df_churn, on="billing_month", how="left").fillna(0)

    # Compute advanced metrics
    df_kpi["starting_mrr"] = df_kpi["total_mrr"].shift(1).fillna(df_kpi["total_mrr"].iloc[0])
    df_kpi["starting_accounts"] = df_kpi["active_accounts"].shift(1).fillna(df_kpi["active_accounts"].iloc[0])
    
    # Churn rates
    df_kpi["logo_churn_rate"] = np.where(df_kpi["starting_accounts"] > 0, df_kpi["churned_accounts"] / df_kpi["starting_accounts"], 0.0)
    df_kpi["revenue_churn_rate"] = np.where(df_kpi["starting_mrr"] > 0, df_kpi["churned_mrr"] / df_kpi["starting_mrr"], 0.0)
    
    # NRR % = (starting_mrr + expansion - contraction - churned_mrr) / starting_mrr * 100
    df_kpi["nrr_percentage"] = np.where(
        df_kpi["starting_mrr"] > 0,
        ((df_kpi["starting_mrr"] + df_kpi["expansion_mrr"] - df_kpi["contraction_mrr"] - df_kpi["churned_mrr"]) / df_kpi["starting_mrr"]) * 100,
        100.0
    )
    
    # LTV = ARPU / Gross Revenue Churn Rate
    df_kpi["avg_ltv"] = np.where(df_kpi["revenue_churn_rate"] > 0.005, df_kpi["arpu"] / df_kpi["revenue_churn_rate"], df_kpi["arpu"] * 24)
    df_kpi["ltv_cac_ratio"] = np.where(df_kpi["avg_cac"] > 0, df_kpi["avg_ltv"] / df_kpi["avg_cac"], 3.5)
    
    # Quick Ratio = (New MRR + Expansion MRR) / (Contraction MRR + Churned MRR)
    churn_loss = df_kpi["contraction_mrr"] + df_kpi["churned_mrr"]
    df_kpi["saas_quick_ratio"] = np.where(churn_loss > 0, (df_kpi["new_mrr"] + df_kpi["expansion_mrr"]) / churn_loss, 4.0)

    # Save to SQLite
    df_kpi.to_sql("agg_executive_saas_kpis", conn, if_exists="replace", index=False)

    # 6. Export Processed Data & Tableau Feeds
    log("EXPORT", "Exporting processed models and Tableau-optimized feeds...")
    
    # Processed CSVs
    pd.read_sql_query("SELECT * FROM dim_accounts", conn).to_csv(os.path.join(PROCESSED_DIR, "dim_accounts.csv"), index=False)
    pd.read_sql_query("SELECT * FROM fct_monthly_billing", conn).to_csv(os.path.join(PROCESSED_DIR, "fct_monthly_billing.csv"), index=False)
    df_cohorts = pd.read_sql_query("SELECT * FROM kpi_monthly_cohorts", conn)
    df_cohorts.to_csv(os.path.join(PROCESSED_DIR, "kpi_monthly_cohorts.csv"), index=False)
    df_kpi.to_csv(os.path.join(PROCESSED_DIR, "agg_executive_saas_kpis.csv"), index=False)

    # Tableau Feeds
    df_kpi.to_csv(os.path.join(TABLEAU_DIR, "tableau_saas_kpi_feed.csv"), index=False)
    df_cohorts.to_csv(os.path.join(TABLEAU_DIR, "tableau_cohort_retention_feed.csv"), index=False)

    # Pricing Gap Feed for Tableau
    pricing_query = """
        SELECT 
            f.billing_month,
            f.plan_tier,
            a.experiment_group,
            COUNT(DISTINCT f.account_id) AS active_accounts,
            AVG(f.tokens_consumed) AS avg_tokens,
            AVG(f.overage_amount) AS avg_overage_charge,
            AVG(f.mrr_amount) AS avg_mrr,
            SUM(f.pricing_gap_applied) AS accounts_facing_pricing_gap
        FROM fct_monthly_billing f
        JOIN dim_accounts a ON f.account_id = a.account_id
        GROUP BY f.billing_month, f.plan_tier, a.experiment_group;
    """
    pd.read_sql_query(pricing_query, conn).to_csv(os.path.join(TABLEAU_DIR, "tableau_pricing_gap_feed.csv"), index=False)

    # 7. Validation Assertions
    log("VALIDATE", "Running data quality & pipeline integrity tests...")
    total_acc_count = conn.execute("SELECT COUNT(*) FROM dim_accounts").fetchone()[0]
    total_fct_count = conn.execute("SELECT COUNT(*) FROM fct_monthly_billing").fetchone()[0]
    total_cohort_count = conn.execute("SELECT COUNT(*) FROM kpi_monthly_cohorts").fetchone()[0]
    
    assert total_acc_count >= 17000, f"Account count {total_acc_count} is less than 17,000!"
    assert total_fct_count > 90000, f"Fact table count {total_fct_count} lower than expected!"
    assert total_cohort_count > 0, "Cohort table is empty!"

    conn.close()

    elapsed = round(time.time() - start_time, 2)
    log("SUCCESS", f"ETL Pipeline successfully completed in {elapsed}s.")
    print("==================================================================")
    print(f"  Accounts Modeled:      {total_acc_count:,}")
    print(f"  Transactions Modeled:  {total_fct_count:,}")
    print(f"  Cohort Slices Created: {total_cohort_count:,}")
    print(f"  Latest Ending MRR:     ${df_kpi['total_mrr'].iloc[-1]:,.2f}")
    print(f"  Latest ARR Run-Rate:   ${df_kpi['total_mrr'].iloc[-1]*12:,.2f}")
    print(f"  Latest Churn Rate:     {df_kpi['logo_churn_rate'].iloc[-1]*100:.2f}%")
    print(f"  Net Retention (NRR):   {df_kpi['nrr_percentage'].iloc[-1]:.1f}%")
    print(f"  Quick Ratio:           {df_kpi['saas_quick_ratio'].iloc[-1]:.2f}x")
    print("==================================================================")

if __name__ == "__main__":
    run_etl()
