#!/usr/bin/env python3
"""
LocoBuzz Solutions - Synthetic B2B SaaS Customer & Transaction Generator
Simulates 17,000+ B2B customer accounts over 12 months with realistic SaaS metrics,
usage logs, cohort churn, and an injected 20 bps pricing gap in Mid-Market accounts.
"""

import os
import csv
import random
import datetime
import numpy as np
import pandas as pd

# Set deterministic seed for reproducibility
np.random.seed(42)
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DATA_DIR, exist_ok=True)

TOTAL_ACCOUNTS = 17250  # 17K+ accounts
MONTHS = 12

INDUSTRIES = [
    "E-Commerce & Retail", "Financial Services", "Telecommunications",
    "Hospitality & Travel", "Healthcare & Pharma", "Tech & Software",
    "Media & Entertainment", "Automotive"
]

REGIONS = ["India (West - Mumbai)", "India (South - Bangalore)", "India (North - NCR)", 
           "Southeast Asia (Singapore)", "Middle East (Dubai)", "Europe (London)"]

PLANS = {
    "Starter": {
        "base_mrr": 299,
        "token_quota": 25000,
        "weight": 0.45,
        "churn_rate": 0.048,
        "cac_mean": 950
    },
    "Growth": {
        "base_mrr": 999,
        "token_quota": 100000,
        "weight": 0.40,
        "churn_rate": 0.038,
        "cac_mean": 2400
    },
    "Enterprise": {
        "base_mrr": 3499,
        "token_quota": 500000,
        "weight": 0.15,
        "churn_rate": 0.015,
        "cac_mean": 6500
    }
}

COMPANY_PREFIXES = [
    "Omni", "Apex", "Nova", "Zeta", "Acu", "Hyper", "Strata", "Pulse", "Verve",
    "Nexis", "Alpha", "Titan", "Crest", "Vanguard", "Kinetix", "Aura", "Matrix",
    "Zenith", "Cobalt", "Beacon", "Sol", "Quant", "BluePeak", "CloudScale"
]

COMPANY_SUFFIXES = [
    "Retail", "Fintech", "Health", "Logistics", "Media", "Labs", "Systems",
    "Networks", "Ventures", "Mobility", "Direct", "Global", "Technologies", "Hub"
]

def generate_company_name(i):
    prefix = random.choice(COMPANY_PREFIXES)
    suffix = random.choice(COMPANY_SUFFIXES)
    return f"{prefix} {suffix} #{i+101}"

def generate_accounts():
    print(f"[1/3] Generating {TOTAL_ACCOUNTS} B2B customer accounts...")
    accounts = []
    
    plan_names = list(PLANS.keys())
    plan_weights = [PLANS[p]["weight"] for p in plan_names]

    for i in range(TOTAL_ACCOUNTS):
        acc_id = f"ACC-{100000 + i}"
        company_name = generate_company_name(i)
        industry = random.choice(INDUSTRIES)
        region = random.choice(REGIONS)
        plan = np.random.choice(plan_names, p=plan_weights)
        
        # Signup month between 0 and 11
        signup_month_offset = np.random.randint(0, 12)
        signup_day = np.random.randint(1, 28)
        signup_date = datetime.date(2025, 1 + signup_month_offset, signup_day)
        
        # Acquisition cost (CAC)
        cac = round(max(300, float(np.random.normal(PLANS[plan]["cac_mean"], PLANS[plan]["cac_mean"] * 0.15))), 2)
        
        # A/B Experiment Assignment (50/50 randomized on eligible accounts)
        experiment_group = "variant" if (hash(acc_id) % 2 == 0) else "control"

        # Seats count
        if plan == "Starter":
            seats = random.randint(2, 5)
        elif plan == "Growth":
            seats = random.randint(6, 20)
        else:
            seats = random.randint(25, 120)

        accounts.append({
            "account_id": acc_id,
            "company_name": company_name,
            "industry": industry,
            "region": region,
            "plan_tier": plan,
            "seats": seats,
            "monthly_token_quota": PLANS[plan]["token_quota"],
            "signup_date": signup_date.strftime("%Y-%m-%d"),
            "signup_month": signup_date.strftime("%Y-%m"),
            "cac": cac,
            "experiment_group": experiment_group
        })

    df_accounts = pd.DataFrame(accounts)
    accounts_csv_path = os.path.join(RAW_DATA_DIR, "raw_accounts.csv")
    df_accounts.to_csv(accounts_csv_path, index=False)
    print(f"      Saved {len(df_accounts):,} accounts to {accounts_csv_path}")
    return df_accounts

def generate_transactions_and_usage(df_accounts):
    print("[2/3] Simulating monthly transactions and product usage logs...")
    transactions = []
    usage_logs = []
    
    txn_counter = 1000001
    log_counter = 5000001

    month_dates = [datetime.date(2025, m, 1) for m in range(1, 13)]

    for _, acc in df_accounts.iterrows():
        acc_id = acc["account_id"]
        plan = acc["plan_tier"]
        signup_date = datetime.datetime.strptime(acc["signup_date"], "%Y-%m-%d").date()
        signup_month_idx = signup_date.month - 1
        group = acc["experiment_group"]
        
        is_churned = False
        
        for m_idx in range(signup_month_idx, 12):
            if is_churned:
                break
                
            tenure_months = m_idx - signup_month_idx
            month_date = month_dates[m_idx]
            
            base_churn = PLANS[plan]["churn_rate"]
            
            # Usage simulation
            base_quota = acc["monthly_token_quota"]
            usage_factor = 0.85 + (tenure_months * 0.07) + float(np.random.normal(0, 0.08))
            tokens_used = int(max(1000, base_quota * usage_factor))
            api_calls = int(tokens_used / random.uniform(8, 14))
            tickets_resolved = int(acc["seats"] * random.uniform(120, 240))
            
            overage_tokens = max(0, tokens_used - base_quota)
            overage_fee = 0.0
            
            pricing_gap_applied = 0
            if plan == "Growth" and overage_tokens > 0:
                if group == "control":
                    # Control has 20 bps effective rate markup on overages
                    unit_rate = 0.012  # Standard rate + 20 bps equivalent
                    overage_fee = round((overage_tokens / 1000) * unit_rate * 100, 2)
                    pricing_gap_applied = 1
                    if tenure_months >= 3:
                        # Bill shock increases churn
                        base_churn *= 1.38
                else:
                    # Variant has optimized pricing: 20 bps lower effective rate + 10% usage buffer
                    unit_rate = 0.010
                    net_overage = max(0, tokens_used - int(base_quota * 1.10))
                    overage_fee = round((net_overage / 1000) * unit_rate * 100, 2)
                    # 14% relative churn reduction
                    base_churn *= 0.86
            elif plan == "Starter":
                if overage_tokens > 0:
                    overage_fee = round((overage_tokens / 1000) * 0.75, 2)
            else: # Enterprise
                if overage_tokens > 0:
                    overage_fee = round((overage_tokens / 1000) * 0.40, 2)
            
            if tenure_months > 0 and random.random() < base_churn:
                is_churned = True
                continue

            base_fee = PLANS[plan]["base_mrr"]
            discount = 0.0
            if tenure_months == 0 and random.random() < 0.20:
                discount = round(base_fee * 0.15, 2)

            total_billed = round(base_fee + overage_fee - discount, 2)
            billing_date = datetime.date(2025, m_idx + 1, min(signup_date.day, 28))

            transactions.append({
                "txn_id": f"TXN-{txn_counter}",
                "account_id": acc_id,
                "billing_date": billing_date.strftime("%Y-%m-%d"),
                "billing_month": month_date.strftime("%Y-%m"),
                "tenure_month": tenure_months,
                "plan_tier": plan,
                "base_amount": base_fee,
                "overage_amount": overage_fee,
                "discount_amount": discount,
                "total_billed": total_billed,
                "currency": "USD",
                "payment_status": "PAID" if random.random() > 0.012 else "FAILED",
                "pricing_gap_applied": pricing_gap_applied
            })
            txn_counter += 1

            usage_logs.append({
                "log_id": f"LOG-{log_counter}",
                "account_id": acc_id,
                "log_month": month_date.strftime("%Y-%m"),
                "ai_sentiment_tokens": tokens_used,
                "tickets_resolved": tickets_resolved,
                "active_agent_seats": acc["seats"],
                "api_calls_count": api_calls
            })
            log_counter += 1

    df_txns = pd.DataFrame(transactions)
    df_usage = pd.DataFrame(usage_logs)

    txns_csv_path = os.path.join(RAW_DATA_DIR, "raw_transactions.csv")
    usage_csv_path = os.path.join(RAW_DATA_DIR, "raw_usage_logs.csv")
    
    df_txns.to_csv(txns_csv_path, index=False)
    df_usage.to_csv(usage_csv_path, index=False)

    print(f"      Saved {len(df_txns):,} transactions to {txns_csv_path}")
    print(f"      Saved {len(df_usage):,} usage logs to {usage_csv_path}")
    return df_txns, df_usage

def main():
    print("==================================================================")
    print("  LocoBuzz Solutions - Synthetic B2B Data Generation Engine       ")
    print("==================================================================")
    df_accounts = generate_accounts()
    df_txns, df_usage = generate_transactions_and_usage(df_accounts)
    print("[3/3] Data synthesis complete.")
    print(f"Total Accounts: {len(df_accounts):,}")
    print(f"Total Transactions: {len(df_txns):,}")
    print(f"Total Usage Logs: {len(df_usage):,}")
    print("==================================================================")

if __name__ == "__main__":
    main()
