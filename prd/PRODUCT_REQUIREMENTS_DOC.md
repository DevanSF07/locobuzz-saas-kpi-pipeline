# Product Requirements Document (PRD)
## B2B SaaS Pricing Optimization & Churn Mitigation Engine
**Organization:** LocoBuzz Solutions  
**Author:** AI Product Manager Intern  
**Location:** Mumbai, India  
**Stakeholders:** VP of Product, Head of Growth, Lead Data Architect, VP Customer Success  
**Scope:** 17,000+ B2B Client Accounts  

---

## 1. Executive Summary & Context
LocoBuzz is an enterprise SaaS platform providing unified customer experience (CX), conversational AI response management, and omnichannel social listening. As the customer base expanded beyond **17,000 active B2B accounts**, executive leadership noticed an unexpected stagnation in Net Revenue Retention (NRR) and a cluster of cancellations among Mid-Market accounts between Month 3 and Month 5 of their contract lifecycle.

This project encompassed:
1. Building an **automated Postgres SQL ETL pipeline** ingesting and transforming 17K+ monthly B2B transaction and product usage logs into structured KPI cohort models.
2. Deploying an **executive Tableau dashboard** providing real-time visibility into MRR waterfalls, logo churn, CAC, and LTV.
3. Conducting **AARRR cohort analysis** that uncovered a hidden **20 basis point (0.20%) unit pricing gap** in AI token overage charges, leading to severe bill shock.
4. Designing and executing a **controlled A/B test** validating a redesigned pricing structure that achieved a **14% relative reduction in customer churn** and protected **$1.98M in Annual Recurring Revenue (ARR)**.

---

## 2. Problem Statement
Mid-Market accounts on the **Growth Tier ($999/mo base)** exhibited a 22.3% annualized churn rate, compared to 1.5% in Enterprise accounts. 
Interviews with Customer Success and billing analysis revealed:
- Rapid adoption of LocoBuzz AI sentiment analysis caused client token usage to exceed their 100,000 monthly quota by Month 3.
- The legacy billing engine applied an aggressive overage markup ($0.0120 per 1K tokens), creating a **20 bps ($0.0020 / 1K tokens)** pricing cliff compared to negotiated rates.
- Clients experienced **"bill shock"** (invoices jumping 25-40% unexpectedly), leading to budget disputes, contract non-renewals, and competitor churn.

---

## 3. Product Goals & Target Metrics

### Primary Metric (North Star)
- **Customer Logo Churn Rate:** Reduce overall client churn rate by **14% relative** (from a 4.3% baseline down to < 3.8%).

### Secondary Financial & Business Metrics
- **Net Revenue Retention (NRR):** Expand from 104.2% to **> 107.0%**.
- **Customer Lifetime Value (LTV):** Increase average Mid-Market account lifespan from 7.8 months to **> 9.5 months** (+21%).
- **LTV : CAC Ratio:** Maintain healthy SaaS unit economics at **> 3.5x** (Achieved: **4.2x**).
- **SaaS Quick Ratio:** Maintain net growth momentum at **> 2.0x** (Achieved: **2.54x**).

### Guardrail Metrics
- **Gross Margin:** Maintain platform inference gross margin above **75%**.
- **Enterprise Deal Value:** Ensure mid-market adjustments do not cannibalize Enterprise pipeline upgrades.

---

## 4. User Personas
1. **Priya Sharma - VP of Customer Experience (Enterprise Buyer):** Needs predictable SaaS expenditures for board reporting. Frustrated by erratic invoice line-items for AI sentiment surges during brand crises.
2. **Rahul Deshmukh - CX Ops Team Lead (Power User):** Manages 15 support agents on LocoBuzz. Wants to enable AI summarization on every ticket without worrying about billing quotas.
3. **Ananya Sen - Chief Commercial Officer / VP Product (Internal Stakeholder):** Requires automated cohort visibility in Tableau to make pricing and packaging decisions backed by statistical rigor.

---

## 5. Technical Solution Architecture

```
[Raw Data Ingestion]
  ├── raw_accounts (17,250 B2B Logos, Tiers, CAC, Cohorts)
  ├── raw_transactions (97,700+ Monthly Invoices, Overages, Status)
  └── raw_usage_logs (AI Tokens Consumed, API Calls, Agent Seats)
         │
         ▼
[Postgres SQL Automated ETL Pipeline]
  ├── DDL & Dimensional Modeling (dim_accounts, fct_monthly_billing)
  ├── Window Functions: LAG() for Revenue Movements (NEW, EXPANSION, CONTRACTION, CHURN)
  └── Cohort Matrix Aggregation (kpi_monthly_cohorts)
         │
         ▼
[Analytical Intelligence & Experimentation]
  ├── AARRR Cohort Retention Heatmap Matrix
  ├── Pricing Gap Detection Engine (20 bps Isolation)
  └── A/B Hypothesis Testing Engine (Z-test, Chi-square, Survival curves)
         │
         ▼
[Executive Visualization Layer]
  ├── Live Interactive Web Dashboard (HTML5/CSS3/Chart.js)
  └── Production Tableau Feeds & Calculated Field Workbooks
```

---

## 6. A/B Testing & Rollout Strategy

### Hypothesis Formulation
> *"If we eliminate the 20 bps overage pricing penalty on Growth accounts by offering a 10% token buffer and capping overages at $0.0100/1K tokens, then Month 3-5 churn will decrease by at least 12%, resulting in net positive ARR expansion despite minor unit fee concessions."*

### Experiment Design
- **Unit of Randomization:** B2B Account ID (`account_id`), randomized 50/50.
- **Control Group (N = 3,430 Growth accounts):** Legacy overage structure ($0.0120 / 1K tokens, zero buffer).
- **Variant Group (N = 3,465 Growth accounts):** Optimized structure ($0.0100 / 1K tokens, 10% token headroom buffer).
- **Duration:** 6 months active cohort observation.

### Results & Verification
- **Control Churn Rate:** 22.30% (765 accounts lost).
- **Variant Churn Rate:** 17.29% (599 accounts lost).
- **Relative Churn Reduction:** **22.5% in Growth tier** (**14.1% across the blended 17K+ client base**).
- **Statistical Significance:** Two-tailed $p = 1.71 \times 10^{-7}$ ($Z = 5.23$, $\chi^2 = 27.01$, statistically significant at $\alpha = 0.01$).
- **Financial Impact:** **+$1.98M in protected ARR**.

---

## 7. Post-Launch Next Steps
1. Permanently roll out the optimized pricing tier to 100% of the customer base.
2. Introduce in-app automated proactive alerts at 80% and 95% token consumption to further assist CX managers.
3. Embed dynamic annual pre-commitment discounts for token overages in FY2026.
