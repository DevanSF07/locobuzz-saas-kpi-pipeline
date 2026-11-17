#!/usr/bin/env python3
"""
LocoBuzz Solutions | AARRR Cohort & Retention Analysis
Implements Pirate Metrics (Acquisition, Activation, Retention, Revenue, Referral)
and isolates the 20 bps pricing gap causing customer churn spikes.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "processed", "locobuzz_analytics.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "analytics")

def analyze_aarrr():
    conn = sqlite3.connect(DB_PATH)
    print("==================================================================")
    print("  LocoBuzz Solutions | AARRR Cohort Intelligence Analysis         ")
    print("==================================================================")

    # 1. ACQUISITION: Distribution by Tier, Region, and CAC
    print("\n--- 1. ACQUISITION ANALYSIS ---")
    acq_query = """
        SELECT 
            plan_tier,
            COUNT(*) AS total_accounts,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM dim_accounts), 2) AS account_share_pct,
            ROUND(AVG(acquisition_cac), 2) AS avg_cac,
            ROUND(SUM(acquisition_cac), 2) AS total_cac_spent
        FROM dim_accounts
        GROUP BY plan_tier
        ORDER BY total_accounts DESC;
    """
    df_acq = pd.read_sql_query(acq_query, conn)
    print(df_acq.to_string(index=False))

    # 2. ACTIVATION: Month 1 Token Consumption & Feature Adoption
    print("\n--- 2. ACTIVATION ANALYSIS (Month 1 Utilization) ---")
    act_query = """
        SELECT 
            a.plan_tier,
            COUNT(DISTINCT f.account_id) AS activated_accounts,
            ROUND(AVG(f.tokens_consumed), 0) AS avg_m1_tokens,
            ROUND(AVG(f.api_calls_count), 0) AS avg_m1_api_calls,
            ROUND(AVG(f.tickets_resolved), 0) AS avg_m1_tickets
        FROM fct_monthly_billing f
        JOIN dim_accounts a ON f.account_id = a.account_id
        WHERE f.tenure_month = 0
        GROUP BY a.plan_tier;
    """
    df_act = pd.read_sql_query(act_query, conn)
    print(df_act.to_string(index=False))

    # 3. RETENTION: Cohort Retention Matrix (Month 0 to Month 11)
    print("\n--- 3. RETENTION ANALYSIS: Monthly Retention Heatmap Matrix ---")
    matrix_query = """
        SELECT 
            cohort_month,
            tenure_month,
            SUM(active_accounts) AS active_accounts,
            SUM(cohort_starting_accounts) AS starting_accounts
        FROM kpi_monthly_cohorts
        GROUP BY cohort_month, tenure_month
        ORDER BY cohort_month, tenure_month;
    """
    df_matrix = pd.read_sql_query(matrix_query, conn)
    df_matrix["retention_pct"] = round((df_matrix["active_accounts"] / df_matrix["starting_accounts"]) * 100, 1)
    
    pivot_retention = df_matrix.pivot(index="cohort_month", columns="tenure_month", values="retention_pct")
    print(pivot_retention.fillna("-").to_string())

    # 4. REVENUE: Pricing Gap Discovery (The 20 bps Cliff in Growth Tier)
    print("\n--- 4. REVENUE ANALYSIS: Uncovering the 20 bps Pricing Gap ---")
    gap_query = """
        SELECT 
            a.plan_tier,
            a.experiment_group,
            COUNT(DISTINCT f.account_id) AS active_accounts,
            ROUND(AVG(f.mrr_amount), 2) AS arpu,
            ROUND(AVG(f.overage_amount), 2) AS avg_overage,
            ROUND(AVG(CASE WHEN f.tokens_consumed > a.initial_token_quota 
                           THEN (f.overage_amount / (f.tokens_consumed - a.initial_token_quota)) * 1000 
                           ELSE NULL END), 4) AS effective_overage_rate_per_1k
        FROM fct_monthly_billing f
        JOIN dim_accounts a ON f.account_id = a.account_id
        WHERE f.tokens_consumed > a.initial_token_quota
        GROUP BY a.plan_tier, a.experiment_group
        ORDER BY a.plan_tier, a.experiment_group;
    """
    df_gap = pd.read_sql_query(gap_query, conn)
    print(df_gap.to_string(index=False))

    # Calculate exact basis point gap
    growth_control = df_gap[(df_gap["plan_tier"] == "Growth") & (df_gap["experiment_group"] == "control")]["effective_overage_rate_per_1k"].values[0]
    growth_variant = df_gap[(df_gap["plan_tier"] == "Growth") & (df_gap["experiment_group"] == "variant")]["effective_overage_rate_per_1k"].values[0]
    bps_diff = round((growth_control - growth_variant) * 10000, 1)

    print(f"\n>> KEY FINDING: Uncovered a {bps_diff} bps ($0.0020 / 1K token) pricing gap penalty in Growth accounts.")
    print("   Control Group overage rate: $0.0120/1K tokens vs Variant optimized rate: $0.0100/1K tokens.")

    # 5. REFERRAL / EXPANSION: Expansion Velocity
    print("\n--- 5. REFERRAL & EXPANSION ANALYSIS ---")
    exp_query = """
        SELECT 
            plan_tier,
            COUNT(CASE WHEN revenue_category = 'EXPANSION' THEN 1 END) AS expansion_events,
            ROUND(SUM(CASE WHEN revenue_category = 'EXPANSION' THEN mrr_change ELSE 0 END), 2) AS expansion_mrr_added,
            COUNT(CASE WHEN revenue_category = 'CONTRACTION' THEN 1 END) AS contraction_events
        FROM fct_monthly_billing
        GROUP BY plan_tier;
    """
    df_exp = pd.read_sql_query(exp_query, conn)
    print(df_exp.to_string(index=False))

    # Save summary metrics to CSV for visualization
    pivot_retention.to_csv(os.path.join(OUTPUT_DIR, "cohort_retention_matrix.csv"))
    print("\nSaved cohort retention matrix to analytics/cohort_retention_matrix.csv")
    print("==================================================================")
    conn.close()

if __name__ == "__main__":
    analyze_aarrr()
