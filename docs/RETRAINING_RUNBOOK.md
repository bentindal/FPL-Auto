# FPL Model Retraining Operational Runbook

**Last Updated:** 2026-05-28  
**Status:** Phase 10 Validated  
**Phase:** 10-model-retraining

---

## 1. Overview

This runbook documents procedures for operating the FPL model retraining pipeline in production (Phase 10+).

### Purpose
Scheduled model retraining every 2 gameweeks automatically updates position-specific ensemble models on live 2024-25 season data. Event-driven drift detection triggers unscheduled retraining if structural changes detected (injuries, formations, fixture changes).

### Frequency
- **Baseline Schedule:** Every 2 gameweeks (GW 2, 4, 6, ..., 38)
- **Emergency Override:** When RMSE exceeds 15% baseline for 2+ consecutive gameweeks
- **Minimum Interval:** 1 gameweek cooldown between scheduled retrains to prevent thrashing

### Orchestration
- **Apache Airflow DAG:** `fpl_retrain_schedule`
- **Airflow Schedule:** Tuesday-Sunday 19:00 UTC (post-match window)
- **Task Flow:** collect → validate → retrain → evaluate → export
- **Expected Runtime:** 5-10 minutes per run

### Contact
For production issues, contact: bentdnl@gmail.com

---

## 2. Prerequisites

### 2.1 Software & Infrastructure
- **Apache Airflow** (v2.0+): Installed and initialized
- **Python 3.10+**: With scikit-learn, pandas, numpy, requests
- **FPL API Access**: Free (no authentication required)
- **Understat API Access**: Free tier available
- **Disk Space**: Minimum 5 GB for models + accumulated data
- **Database**: PostgreSQL for Airflow metadata (default: SQLite for development)

### 2.2 Airflow Setup
```bash
# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com

# Start scheduler (background)
airflow scheduler &

# Start webserver (background)
airflow webserver &
```

**Verification:**
- Airflow webserver accessible at `http://localhost:8080`
- Scheduler running without errors in logs

### 2.3 Data Directory Structure
```
/Users/bentindal/Desktop/coding/FPL-Auto/
├── data/
│   ├── 2019-20/ ... 2023-24/  (historical Vaastav CSVs)
│   └── 2024-25/
│       └── accumulated_gw.csv  (grows each GW)
├── predictions/
│   └── 2024-25/
│       ├── GW2/ (GK.tsv, DEF.tsv, MID.tsv, FWD.tsv)
│       ├── GW4/
│       └── ...
├── models/
│   ├── gk_model_gw2.pkl
│   ├── def_model_gw2.pkl
│   └── ... (saved per retrain event)
└── dags/
    └── fpl_retrain.py  (Airflow DAG definition)
```

### 2.4 API Credentials (Optional)
- **FPL API**: No authentication required (public)
- **Understat API**: Free tier available (no key needed for basic endpoints)

---

## 3. Execution Workflow

### 3.1 Manual Trigger (Development/Testing)
```bash
# Trigger DAG once
airflow dags trigger fpl_retrain_schedule

# View DAG runs
airflow dags list-runs --dag-id fpl_retrain_schedule
```

### 3.2 Automatic Execution (Production)
Airflow scheduler automatically runs DAG on schedule:
- **Schedule:** `0 19 * * 2-7` (19:00 UTC, Tuesday-Sunday)
- **Backfill:** If missed, next run will catch up automatically

### 3.3 Task Flow Visualization
1. **collect_live_data** — Fetch FPL API + Understat data for current GW
   - Inputs: FPL API endpoints, accumulated_gw.csv
   - Outputs: GW data with RMSE, MAE, R², Spearman metrics
   - Duration: ~1 minute

2. **validate_data** — QA checks (>500 players, >400 actuals, valid positions)
   - Inputs: GW data
   - Outputs: Validation report (pass/fail)
   - Duration: ~10 seconds

3. **retrain_models** — If GW is even (2, 4, 6, ...) or drift detected
   - Inputs: accumulated_gw.csv + historical 2019-2023 data
   - Outputs: Position-specific ensemble models (GK, DEF, MID, FWD)
   - Duration: 3-5 minutes (longer first run)
   - Logic: `if gw % 2 == 0 or drift_detected: retrain()`

4. **evaluate_performance** — Compute metrics and check drift thresholds
   - Inputs: Trained models, GW actuals
   - Outputs: RMSE, MAE, R², Spearman per position
   - Duration: ~1 minute

5. **export_predictions** — Write TSV files for manager.py consumption
   - Inputs: Models, 6-GW lookahead parameters
   - Outputs: `predictions/2024-25/GW{n}/{GK,DEF,MID,FWD}.tsv`
   - Duration: ~30 seconds

### 3.4 Integration with manager.py
```python
# manager.py automatically consumes retraining predictions
from fpl_auto.data import get_fpl_data

fpl_data = get_fpl_data('data/', '2024-25')
# fpl_data loads predictions from predictions/{season}/GW{n}/{pos}.tsv
# Caching ensures efficient lookup during season simulation

# Run season with latest retraining predictions
python3 manager.py -season 2024-25
```

---

## 4. Monitoring

### 4.1 Airflow Logs
```bash
# View DAG logs
airflow logs -d fpl_retrain_schedule -t collect_live_data

# View specific task run
airflow logs -d fpl_retrain_schedule -t retrain_models --execution-date 2024-08-27 19:00:00
```

### 4.2 Metrics Dashboard
After each retrain, metrics saved to `tests/results/live_retraining_metrics_2024-25.csv`:
```
gw,position,rmse,mae,r2,spearman,drift_status,notes
1,GK,1.0317,0.5811,0.4617,0.8141,NO,Baseline
2,GK,1.0409,0.6696,0.6185,0.9330,NO,Retrain
...
```

**Weekly Review Script:**
```bash
# Print metrics summary
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('tests/results/live_retraining_metrics_2024-25.csv')
latest_gw = df['gw'].max()

print(f"Metrics Summary - GW {latest_gw}")
print(df[df['gw'] == latest_gw][['position', 'rmse', 'mae', 'r2', 'spearman']].to_string(index=False))
EOF
```

### 4.3 Alert Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| **RMSE** | >15% above 4-GW rolling mean | Investigate structural change; consider unscheduled retrain |
| **MAE** | >0.8 points/player | Log warning; may indicate systematic bias |
| **R²** | <0.80 | Consider increasing retraining frequency to 1 GW |
| **Spearman** | <0.85 | Ranking quality degraded; impacts captain selection |
| **Task Failure** | Any task fails | Check logs; may indicate API outage or data corruption |

### 4.4 Key Metrics Explanation

- **RMSE (Root Mean Squared Error):** How far predictions deviate from actuals on average. Lower is better. Baseline (2019-2023): ~0.96
- **MAE (Mean Absolute Error):** Average absolute difference. Baseline: ~0.56 points/player
- **R² (Coefficient of Determination):** How much variance explained (0-1 scale). Baseline: ~0.58
- **Spearman (Rank Correlation):** How well ranking predictions match actual ranking (important for captain selection). Baseline: ~0.88

---

## 5. Alerts & Recovery

### 5.1 Scenario: Drift Detected (RMSE >15% for 2+ GWs)

**Investigation:**
1. Check recent injuries/suspensions via FPL API:
   ```python
   from fpl_auto.retrainer import FPLDataSource
   source = FPLDataSource()
   players = source.fetch_bootstrap_static()['elements']
   status_changes = [p for p in players if p['status'] != 'a']
   print(f"Unavailable players: {len(status_changes)}")
   ```

2. Check fixture difficulty spike:
   ```python
   fixtures = source.fetch_fixtures()
   difficult_fixtures = fixtures[fixtures['difficulty'] >= 4]
   print(f"High-difficulty fixtures: {len(difficult_fixtures)}")
   ```

3. Inspect actual vs predicted distribution:
   ```bash
   python3 << 'EOF'
   import pandas as pd
   df = pd.read_csv('data/2024-25/accumulated_gw.csv')
   recent = df[df['gw'].isin([gw-1, gw])].groupby('gw')[['xp', 'points']].agg(['mean', 'std'])
   print(recent)
   EOF
   ```

**Recovery:**
- If structural change confirmed (major injuries): **Trigger unscheduled retrain**
  ```bash
  airflow dags trigger fpl_retrain_schedule --conf '{"force_retrain": true}'
  ```

- If false alarm (noise): **Increase threshold to 20% or decrease frequency to 1 GW**
  - Edit `fpl_auto/retrainer.py`: Change `drift_threshold_factor = 1.15` → `1.20`
  - Commit and push: `git add fpl_auto/retrainer.py && git commit -m "tune(retraining): increase drift threshold to 20%"`

- If persistent: **Consider external feature additions**
  - Phase 11: Add fixture difficulty weighting, injury prediction models

### 5.2 Scenario: API Failure (FPL or Understat Timeout)

**Diagnosis:**
```bash
# Check FPL API status (manual)
curl -I https://fantasy.premierleague.com/api/bootstrap-static/ | head -5

# View error logs
airflow logs -d fpl_retrain_schedule -t collect_live_data | tail -20
```

**Recovery:**
1. **If FPL API down:** Retry automatically (Airflow has 1 retry built-in)
   - Wait 10 minutes, airflow will retry
   - Manual retry: `airflow tasks clear fpl_retrain_schedule -t collect_live_data`

2. **If Understat API down (fallback available):** 
   - retrainer.py falls back to FPL-only data (logs warning)
   - Predictions still generated, quality slightly reduced

3. **If both fail:** Escalate
   - Email: bentdnl@gmail.com
   - Manual rerun available once APIs recover
   - No data loss (accumulated_gw.csv persists)

### 5.3 Scenario: Model Training Timeout (>10 min)

**Diagnosis:**
```bash
# Check accumulated_gw.csv size
ls -lh data/2024-25/accumulated_gw.csv

# If >100 MB: Archive old GWs to compressed file
tar -czf data/2024-25/gw1-20_archive.tar.gz data/2024-25/accumulated_gw.csv
```

**Recovery:**
1. **Reduce model complexity:**
   - Edit `fpl_auto/retrainer.py`: Change `n_estimators = 500` → `300`
   - Commit: `git add fpl_auto/retrainer.py && git commit -m "perf(retraining): reduce n_estimators to 300"`

2. **Increase Airflow task timeout:**
   - Edit `dags/fpl_retrain.py`:
     ```python
     retrain_task = PythonOperator(
         task_id='retrain_models',
         python_callable=retrain_on_schedule,
         execution_timeout=timedelta(minutes=15)  # Increase from 10
     )
     ```

3. **Archive old data:**
   ```bash
   # Move GW1-20 to archive (if needed to reduce training size)
   # Careful: Only after GW20 completed and validated
   ```

### 5.4 Scenario: Prediction Export Fails (TSV Write Error)

**Diagnosis:**
```bash
# Check disk space
df -h /Users/bentindal/Desktop/coding/FPL-Auto/

# Check permissions
ls -ld predictions/2024-25/
```

**Recovery:**
1. **Free disk space:**
   ```bash
   # If <5 GB available: archive old predictions
   tar -czf predictions/2024-25_archive_gw1-10.tar.gz predictions/2024-25/GW{1..10}
   ```

2. **Fix permissions:**
   ```bash
   chmod 755 predictions/2024-25/
   ```

3. **Retry export task:**
   ```bash
   airflow tasks clear fpl_retrain_schedule -t export_predictions
   airflow dags trigger fpl_retrain_schedule
   ```

---

## 6. Maintenance

### 6.1 Weekly Review
Every Tuesday (before Airflow run):
```bash
# Check metrics from previous week
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('tests/results/live_retraining_metrics_2024-25.csv')

# Last 4 GWs
recent = df[df['gw'].isin([df['gw'].max()-3, df['gw'].max()-2, df['gw'].max()-1, df['gw'].max()])]
print(recent[['gw', 'position', 'rmse', 'r2']].to_string(index=False))

# Check for any drift flags
if (recent['drift_status'] == 'YES').any():
    print("\n⚠️ Drift detected! Review needed.")
EOF
```

### 6.2 Monthly Evaluation
First of each month:
```bash
# Check if 2-GW frequency appropriate
python3 << 'EOF'
import pandas as pd
import numpy as np

df = pd.read_csv('tests/results/live_retraining_metrics_2024-25.csv')

# Compute stability metric: std-dev / mean of R² across recent GWs
recent_r2 = df[df['gw'] > df['gw'].max() - 8]['r2'].values
stability = 1 - (np.std(recent_r2) / np.mean(recent_r2))

print(f"Model Stability (recent 8 GWs): {stability:.3f}")
if stability > 0.90:
    print("  → Very stable (could reduce to 4-GW frequency if desired)")
elif stability > 0.85:
    print("  → Stable (2-GW frequency appropriate)")
else:
    print("  → Low stability (consider 1-GW frequency)")
EOF
```

### 6.3 Season End (GW38)
```bash
# Archive all models and metrics
tar -czf models_season_2024-25_final.tar.gz models/ tests/results/

# Prepare for next season (2025-26)
mkdir -p data/2025-26 predictions/2025-26

# Compute baseline metrics for 2025-26
# (Models trained on 2019-2024 baseline; first GWs of 2025-26 compared to this baseline)
```

---

## 7. FAQ

### Q: Why not retrain weekly?

**A:** Research (Arxiv 2505.00356) on 40K+ time-series shows 2-4 GW frequency optimal:
- Weekly retraining 75% more expensive (compute, deployment risk)
- <2% accuracy improvement vs 2-GW schedule
- Models trained on 5 years historical (2019-2023) capture seasonal patterns
- Individual GW variance doesn't require constant updates

### Q: What if drift is detected?

**A:** Drift detection (RMSE >15% above 4-GW baseline) suggests structural change:
1. Investigate cause: injuries, fixture spike, formations
2. If confirmed: Trigger unscheduled retrain immediately
3. If false alarm: Increase threshold or decrease frequency
4. Log cause in `deferred-items.md` for post-season audit

### Q: Can I manually force a retrain?

**A:** Yes, for emergency retraining:
```python
from fpl_auto.retrainer import FPLModelRetrainer

retrainer = FPLModelRetrainer('data/', 'predictions/')
retrainer.retrain_on_schedule(gw=X, force=True)  # Retrain regardless of schedule
retrainer._checkpoint(X)  # Save models
```

Or via Airflow:
```bash
airflow dags trigger fpl_retrain_schedule --conf '{"force_retrain": true, "gw": 15}'
```

### Q: How do I validate predictions are correct?

**A:** Compare manager.py output with predictions:
```python
import pandas as pd

# Load predictions exported for GW2
gk_pred = pd.read_csv('predictions/2024-25/GW2/GK.tsv', sep='\t')
print(gk_pred.head())
# Expected: player_id, xp columns

# Load accumulated GW data
accumulated = pd.read_csv('data/2024-25/accumulated_gw.csv')
gw2_gk = accumulated[(accumulated['gw'] == 2) & (accumulated['position'] == 'GK')]

# Verify predictions are within expected range (0-10 xP)
assert gk_pred['xp'].min() > 0 and gk_pred['xp'].max() < 10
print("✓ Predictions validated")
```

### Q: What if I need to change thresholds?

**A:** Edit `fpl_auto/retrainer.py` constants:
```python
# Current thresholds
DRIFT_THRESHOLD_FACTOR = 1.15  # 15% above baseline
MIN_RMSE_THRESHOLD = 1.5  # std-devs above baseline
RETRAINING_FREQUENCY_GW = 2  # Every 2 GWs
MIN_RETRAINING_INTERVAL = 1  # GW cooldown
```

After changes:
```bash
git add fpl_auto/retrainer.py
git commit -m "tune(retraining): adjust drift threshold to 20%"
airflow dags unpause fpl_retrain_schedule  # Resume if paused
```

### Q: What happens if accumulated_gw.csv is corrupted?

**A:** Backup and recover:
```bash
# Backup corrupted file
cp data/2024-25/accumulated_gw.csv data/2024-25/accumulated_gw.csv.bak

# Restore from last clean commit
git checkout data/2024-25/accumulated_gw.csv

# Re-run collect task for missing GWs
airflow tasks clear fpl_retrain_schedule -t collect_live_data -s 2024-08-20 -e 2024-08-27
```

### Q: How are predictions used by manager.py?

**A:** In `fpl_auto/data.py`:
```python
def get_predictions(gw, position):
    """Load predictions from predictions/{season}/GW{gw}/{position}.tsv"""
    tsv_file = f'predictions/{self.season}/GW{gw}/{position}.tsv'
    df = pd.read_csv(tsv_file, sep='\t')  # xp column
    return df  # Manager uses xp for team decisions
```

Retraining predictions automatically consumed by manager.py during season simulation.

---

## 8. Support & Escalation

### For Operational Issues:
- **Email:** bentdnl@gmail.com
- **Logs:** `/Users/bentindal/Desktop/coding/FPL-Auto/logs/`
- **Airflow UI:** http://localhost:8080 (development)

### For Development Issues:
- Review Phase 10 research: `.planning/research/10-MODEL-RETRAINING-RESEARCH.md`
- Review Phase 10 context: `.planning/phases/10-model-retraining/10-CONTEXT.md`
- Test suite: `tests/test_live_retraining.py`

---

**End of Runbook**  
**Phase 10 Status:** Complete (validated on 2024-25 season GW1-5)  
**Next Phase:** Phase 11 - Drift Monitoring Dashboard & Fixture Difficulty Integration
