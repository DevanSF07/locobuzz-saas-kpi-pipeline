/**
 * LocoBuzz Solutions | Executive SaaS Analytics Dashboard Controller
 * Powered by SQL Feeds & Cohort Intelligence
 */

// Embedded Data extracted from LocoBuzz SQL Pipeline
const SAAS_DATA = {
  months: ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"],
  mrr: [1.32, 2.61, 3.91, 5.23, 6.54, 7.85, 9.17, 10.46, 11.77, 13.06, 14.34, 15.63], // in Millions
  newMrr: [1.32, 1.30, 1.31, 1.33, 1.32, 1.32, 1.33, 1.30, 1.32, 1.30, 1.29, 1.30],
  expansionMrr: [0, 0.08, 0.14, 0.21, 0.29, 0.38, 0.47, 0.56, 0.66, 0.76, 0.86, 0.96],
  churnedMrr: [0, 0.04, 0.09, 0.15, 0.22, 0.31, 0.41, 0.52, 0.64, 0.77, 0.90, 1.04],
  churnRate: [0.0, 3.2, 3.5, 3.8, 4.1, 4.3, 4.2, 4.0, 3.9, 3.8, 3.7, 3.7],
  nrr: [100.0, 103.2, 104.5, 105.1, 106.0, 106.4, 106.8, 107.1, 107.3, 107.5, 107.8, 108.2],
  
  // Cohort Retention Heatmap Matrix
  cohorts: [
    { cohort: "2025-01", size: 1438, ret: [98.7, 95.0, 90.9, 86.9, 83.7, 79.9, 77.2, 74.2, 71.0, 68.5, 66.3, 63.6] },
    { cohort: "2025-02", size: 1421, ret: [99.0, 95.5, 92.2, 89.1, 85.6, 81.6, 77.6, 74.5, 71.7, 69.0, 66.3] },
    { cohort: "2025-03", size: 1445, ret: [99.1, 95.5, 91.9, 88.8, 84.4, 81.3, 77.4, 74.4, 71.7, 68.3] },
    { cohort: "2025-04", size: 1432, ret: [98.9, 95.6, 92.3, 87.5, 84.6, 81.2, 78.3, 74.3, 71.3] },
    { cohort: "2025-05", size: 1450, ret: [98.5, 95.0, 91.8, 88.1, 84.6, 80.5, 77.1, 73.1] },
    { cohort: "2025-06", size: 1419, ret: [99.0, 94.9, 91.2, 88.0, 84.6, 80.8, 78.1] },
    { cohort: "2025-07", size: 1441, ret: [98.6, 95.4, 92.5, 87.7, 85.1, 81.1] },
    { cohort: "2025-08", size: 1436, ret: [98.5, 95.7, 91.7, 88.3, 84.7] },
    { cohort: "2025-09", size: 1452, ret: [98.7, 94.3, 91.0, 87.6] },
    { cohort: "2025-10", size: 1428, ret: [98.9, 95.5, 91.7] },
    { cohort: "2025-11", size: 1440, ret: [98.8, 95.0] },
    { cohort: "2025-12", size: 1448, ret: [98.3] }
  ],

  // Growth Tier 20 bps Pricing Gap Data
  pricingGap: {
    controlOverageRate: "$0.0120 / 1K Tokens",
    variantOverageRate: "$0.0100 / 1K Tokens",
    gapBps: "20.0 bps ($0.0020 penalty)",
    controlLifespan: "7.8 months",
    variantLifespan: "9.6 months (+23%)",
    relativeChurnCut: "14.1%",
    annualSavings: "$1,985,377"
  }
};

document.addEventListener("DOMContentLoaded", () => {
  renderCohortHeatmap();
  initMRRChart();
  initPricingGapChart();
  setupFilterListeners();
});

function renderCohortHeatmap() {
  const tbody = document.getElementById("cohortTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  SAAS_DATA.cohorts.forEach(c => {
    const row = document.createElement("tr");
    
    // Cohort Month & Size
    const headTd = document.createElement("td");
    headTd.className = "cohort-header";
    headTd.innerHTML = `<strong>${c.cohort}</strong> <span style="color:#64748b">(${c.size.toLocaleString()})</span>`;
    row.appendChild(headTd);

    // Tenure cells (0 to 11)
    for (let t = 0; t <= 11; t++) {
      const td = document.createElement("td");
      if (t < c.ret.length) {
        const val = c.ret[t];
        td.textContent = `${val.toFixed(1)}%`;
        if (val >= 90) td.className = "cell-high";
        else if (val >= 80) td.className = "cell-med-high";
        else if (val >= 70) td.className = "cell-med";
        else td.className = "cell-low";
      } else {
        td.textContent = "-";
        td.className = "cell-empty";
      }
      row.appendChild(td);
    }
    tbody.appendChild(row);
  });
}

function initMRRChart() {
  const ctx = document.getElementById("mrrChart");
  if (!ctx) return;

  new Chart(ctx, {
    type: "line",
    data: {
      labels: SAAS_DATA.months,
      datasets: [
        {
          label: "Ending MRR ($M)",
          data: SAAS_DATA.mrr,
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.12)",
          fill: true,
          tension: 0.35,
          borderWidth: 3,
          pointBackgroundColor: "#38bdf8",
          pointRadius: 4
        },
        {
          label: "New MRR ($M)",
          data: SAAS_DATA.newMrr,
          borderColor: "#10b981",
          borderDash: [5, 5],
          borderWidth: 2,
          pointRadius: 0,
          fill: false
        },
        {
          label: "Churned MRR ($M)",
          data: SAAS_DATA.churnedMrr,
          borderColor: "#f43f5e",
          borderWidth: 2,
          pointRadius: 0,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: "#1e293b",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          titleColor: "#f8fafc",
          bodyColor: "#cbd5e1",
          padding: 10
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#64748b" }
        },
        y: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: {
            color: "#64748b",
            callback: (v) => "$" + v + "M"
          }
        }
      }
    }
  });
}

function initPricingGapChart() {
  const ctx = document.getElementById("pricingChart");
  if (!ctx) return;

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Starter Tier", "Growth (Control)", "Growth (Variant)", "Enterprise Tier"],
      datasets: [
        {
          label: "Base Unit Rate ($ / 1K Tokens)",
          data: [0.0075, 0.0100, 0.0100, 0.0040],
          backgroundColor: "#6366f1",
          borderRadius: 4
        },
        {
          label: "Overage Penalty (20 bps Gap)",
          data: [0.0, 0.0020, 0.0, 0.0],
          backgroundColor: "#f43f5e",
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#94a3b8", font: { size: 12 } } },
        tooltip: {
          callbacks: {
            label: (item) => `${item.dataset.label}: $${item.raw.toFixed(4)} / 1K`
          }
        }
      },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color: "#94a3b8" } },
        y: {
          stacked: true,
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: {
            color: "#64748b",
            callback: (v) => "$" + v.toFixed(4)
          }
        }
      }
    }
  });
}

function setupFilterListeners() {
  const tierFilter = document.getElementById("filterTier");
  const expFilter = document.getElementById("filterExperiment");

  function applyFilters() {
    const tier = tierFilter ? tierFilter.value : "all";
    const exp = expFilter ? expFilter.value : "all";

    const mrrEl = document.getElementById("kpiEndingMrr");
    const churnEl = document.getElementById("kpiChurnRate");

    if (exp === "control") {
      if (churnEl) churnEl.textContent = "4.3%";
      if (churnEl) churnEl.nextElementSibling.querySelector("span").textContent = "+0.6% vs benchmark";
    } else if (exp === "variant") {
      if (churnEl) churnEl.textContent = "3.7%";
      if (churnEl) churnEl.nextElementSibling.querySelector("span").textContent = "-14% relative cut";
    } else {
      if (churnEl) churnEl.textContent = "3.7%";
      if (churnEl) churnEl.nextElementSibling.querySelector("span").textContent = "-14% cut via A/B";
    }
  }

  if (tierFilter) tierFilter.addEventListener("change", applyFilters);
  if (expFilter) expFilter.addEventListener("change", applyFilters);
}

function exportTableauFeed() {
  alert("Downloading Tableau Feed CSV files from /dashboard/tableau_feeds/...\nFiles:\n- tableau_saas_kpi_feed.csv\n- tableau_cohort_retention_feed.csv\n- tableau_pricing_gap_feed.csv");
  window.open("tableau_feeds/tableau_saas_kpi_feed.csv");
}
