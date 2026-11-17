#!/bin/bash
# ==============================================================================
# LocoBuzz Solutions | End-to-End Pipeline & Analytics Runner
# One-click execution for data synthesis, ETL processing, AARRR & A/B testing
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"

echo "=========================================================================="
echo "  LOCOBUZZ SOLUTIONS | AI PRODUCT MANAGER INTERN PORTFOLIO PIPELINE      "
echo "  Scale: 17K+ B2B Customers | Automated Postgres ETL & Tableau Dashboards"
echo "=========================================================================="
echo ""

# 1. Generate Synthetic 17K+ B2B Dataset
echo "[Step 1/4] Running Synthetic Data Generator..."
python3 "$DIR/generate_synthetic_data.py"
echo ""

# 2. Execute SQL ETL Pipeline
echo "[Step 2/4] Executing Automated SQL ETL Pipeline..."
python3 "$DIR/etl_pipeline.py"
echo ""

# 3. AARRR Cohort & Pricing Gap Analysis
echo "[Step 3/4] Running AARRR Cohort Analysis..."
python3 "$PROJECT_ROOT/analytics/aarrr_cohort_analysis.py"
echo ""

# 4. A/B Testing Statistical Validation
echo "[Step 4/4] Executing A/B Testing Validation..."
python3 "$PROJECT_ROOT/analytics/ab_testing_validation.py"
echo ""

echo "=========================================================================="
echo "  PIPELINE EXECUTION FINISHED SUCCESSFULLY!                              "
echo "  - Processed Database: data/processed/locobuzz_analytics.db            "
echo "  - Tableau Feeds:      dashboard/tableau_feeds/*.csv                     "
echo "  - Live Dashboard:     dashboard/index.html (Open in browser)           "
echo "=========================================================================="
