# 2025-26 Season Analysis & 2026-27 Prep

**Status:** 2025-26 season complete (missed live retraining window)  
**Priority 1 (Complete):** Generated xP predictions for 2025-26 vs actuals  
**Priority 2 (Next):** Prepare Phase 10 Airflow for live 2026-27 season (August 2026)

---

## 2025-26 Prediction Analysis

### Results Summary

Two approaches tested on completed 2025-26 season:

#### Baseline (Position + GW Averages)
- RMSE: 1.92–2.51
- MAE: 1.29–1.61
- R²: ~0 (no predictive power)
- Spearman: ~0.01 (essentially random)

#### Form-Weighted (Recent-Weighted Per-Player)
- RMSE: 3.14–3.50
- MAE: 2.05–2.35
- R²: -0.22 to -0.49 (worse than baseline, overfitting)
- Spearman: 0.01–0.15 (weak signal)

### Key Finding

**Simple historical averaging underperforms 2025-26 because:**
- Squad composition changed between 2020-25 baseline and 2025-26
- Player form weights don't capture tactical/positional shifts
- Cross-season patterns are weak (different teams, formations, injuries)

**Solution:** Phase 10's approach (ensemble models + live retraining every 2 GWs) designed to handle this by:
- Training on accumulated live data (not historical)
- Detecting drift with PELT (adapts to new patterns)
- Position-specific ensembles (captures positional nuances)

---

## Lesson: Why Phase 10 Was Needed

The 2025-26 shortfall validates Phase 10's design:

| Limitation (2025-26) | Phase 10 Solution |
|---|---|
| Weak cross-season transfer | Expanding window: 2019-2024 baseline + live 2024-25 |
| No drift detection | PELT change-point analysis (15% RMSE threshold) |
| Static models | Retrain every 2 GWs, unscheduled on drift |
| Generic position models | Ensemble (XGBoost + RF) per position with optimal hyperparams |

---

## 2026-27 Preparation (Priority 2)

### Timeline

| Date | Action | Owner |
|------|--------|-------|
| **August 2026** | 2026-27 season starts, GW1 data arrives | FPL |
| **Aug 15, 2026** | Deploy Phase 10 Airflow DAG | You |
| **GW1-2** | Retrain on 2019-25 baseline + GW1-2 live | Airflow (auto) |
| **GW3-38** | Continuous 2-GW retraining + drift monitoring | Airflow (auto) |

### Deployment Checklist

- [ ] **Dependencies installed** (Apache Airflow, scikit-learn, statsmodels)
  - `pip install apache-airflow scikit-learn pandas statsmodels`

- [ ] **Airflow DAG deployed**
  - Copy `dags/fpl_retrain.py` to Airflow DAGs directory

- [ ] **Data pipeline running**
  - Verify `LiveDataCollector` fetches FPL API + Understat post-GW

- [ ] **Thresholds configured**
  - RMSE drift: 15% above baseline
  - MAE threshold: 0.8 pts/player
  - R²: >0.80
  - Spearman: >0.85

- [ ] **Monitoring dashboard active**
  - Airflow UI at http://localhost:8080
  - Check `ModelMonitor` metrics post-GW

- [ ] **Runbook ready**
  - `docs/RETRAINING_RUNBOOK.md` (8 sections, 511 lines)
  - Covers setup, execution, monitoring, alerts, recovery

### Key Files for 2026-27

**Implementation:**
- `fpl_auto/retrainer.py` — FPLModelRetrainer (core logic)
- `dags/fpl_retrain.py` — Airflow DAG (post-GW schedule)
- `fpl_auto/data.py` — Extended for prediction caching

**Documentation:**
- `docs/RETRAINING_RUNBOOK.md` — Operational guide
- `.planning/phases/10-model-retraining/10-IMPLEMENTATION.md` — Design decisions
- `.planning/LOCKED_STRATEGIES.md` — Phase 10 section (locked decisions)

**Configuration:**
- `predictions/{season}/GW{n}/{pos}.tsv` — Output format (consumed by manager.py)
- Airflow schedule: Tue-Sun 19:00 UTC (post-match)

---

## Quick Start (August 2026)

```bash
# 1. Install deps
pip install apache-airflow scikit-learn pandas numpy statsmodels

# 2. Deploy DAG
cp dags/fpl_retrain.py ~/airflow/dags/

# 3. Initialize Airflow
airflow db init

# 4. Start scheduler
airflow scheduler &

# 5. Monitor
airflow webui  # http://localhost:8080

# 6. Trigger DAG after GW1 results arrive
airflow dags trigger fpl_retrain_schedule
```

---

## Why This Works for 2026-27

1. **Live data accumulation** — No cross-season transfer issues
2. **Drift detection** — Catches formation/injury changes mid-season
3. **Adaptive retraining** — 2-GW cycle matches FPL week structure
4. **Position specificity** — GK/DEF/MID/FWD models optimized separately
5. **Manager.py integration** — Seamless TSV prediction format

---

## Files Generated This Session

- `predict_2025_26.py` — Baseline analysis (simple averages)
- `predict_2025_26_v2.py` — Form-weighted analysis
- `.planning/2025-26-ANALYSIS.md` — This file
- `.planning/phases/10-model-retraining/2025-26-formweighted-analysis.csv` — Results

---

## Next Steps

1. **Archive 2025-26 analysis** — Document lessons learned
2. **Confirm August 2026 prep** — Install dependencies, test DAG deployment
3. **Phase 11** — Fixture difficulty weighting, injury prediction (Phase 11 scope)

---

*Generated: 2026-05-28*  
*Status: Ready for 2026-27 live retraining*
