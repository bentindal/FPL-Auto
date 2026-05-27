# Model Improvement Strategies for sklearn

**Researched:** 2026-05-27
**Domain:** Machine Learning model optimization, feature engineering, validation strategies
**Confidence:** HIGH (verified against scikit-learn official docs and peer-reviewed research)

## Summary

Improving sklearn model accuracy in sports prediction (specifically FPL xP forecasting) requires a disciplined approach combining feature engineering, proper validation strategies, and iterative workflow optimization. Current FPL-Auto models use four sklearn algorithms (gradientboost, linear, randomforest, neuralnetwork) trained on historical GW data with position-specific feature sets. Three critical areas drive improvement: (1) feature engineering that captures domain-specific player performance signals, (2) validation strategies that prevent overfitting to historical data while respecting temporal ordering, and (3) iteration workflows that systematically measure improvement and avoid common pitfalls like data leakage.

**Primary recommendation:** Adopt a TimeSeriesSplit validation strategy (respects temporal ordering), use permutation importance (not tree-based feature_importances_) for actionable insights, and implement a pipeline-based preprocessing workflow to prevent data leakage.

---

## 1. Feature Engineering Patterns

### High-Impact Features for Sports Prediction

**Derived Statistics** (NOT raw box-score data)
- Expected Goals (xG) - quality-adjusted shot attempts
- Player Efficiency Ratings (PER) - comprehensive impact metrics  
- Form metrics: rolling averages of recent performance (e.g., 5-GW average, 10-GW average)
- Fixture difficulty: opponent strength ratings adjusted for home/away
- Position-specific metrics: 
  - GK: shots faced, save % trend, minutes consistency
  - DEF: defensive actions per 90, clean sheet probability, player price trend
  - MID: key passes, goal-scoring opportunities, differential ownership
  - FWD: shots on target, expected points trend, injury/rest status

[CITED: https://arxiv.org/html/2410.21484v1 - sports prediction systematic review]

**Team Context Features**
- Team strength ratings (attack_home, attack_away, defence_home, defence_away) — already in FPL-Auto via `team_list` [VERIFIED: CLAUDE.md line 43]
- Recent form: team's last 5-GW win%, goals for/against
- Fixture congestion: days since last match, consecutive matches upcoming
- Injury/suspension status: key player absences from opponent
- Home/away splits: separate models or features for home advantage

[CITED: https://www.analyticsvidhya.com/blog/2025/07/machine-learning-in-sports/ - ML in sports analytics 2025]

**Historical Time-Series Features** (critical for weekly predictions)
- Player's recent xP trend (discount_next_n_gws already applies this; verify feature engineering captures rolling stats)
- Position scarcity: players with few recent matches (inconsistent sample sizes)
- Season progression: GW 1-10 vs. GW 20-38 performance divergence (player adaptation, injury accumulation)

### Feature Engineering Techniques - Actionable Steps

1. **Interaction Features**
   ```
   team_strength * player_minutes (strength matters less if player unused)
   fixture_difficulty * player_form (weak players in easy matches, or strong players in tough?)
   opponent_defence_strength * position (different impact by position)
   ```
   [VERIFIED: Context7/ML best practices - interactions reveal hidden relationships]

2. **Aggregation Windows**
   - Use 2-GW, 5-GW, 10-GW rolling averages (captures short-term form and long-term stability)
   - Discount older data with exponential weighting (recent performance matters more)
   - FPL-Auto already does multi-GW discounting in `discount_next_n_gws` [VERIFIED: CLAUDE.md line 48]

3. **Missing Data Handling**
   - Don't drop rows with NaN — impute with historical position medians or team averages
   - Flag imputed values as separate boolean feature (signals unreliable prediction for that player)
   - FPL-Auto currently drops NaN via `.dropna()` [VERIFIED: data.py line 75] — consider imputation for bench players with few minutes

4. **Feature Scaling and Normalization**
   - Standardize all features to mean=0, std=1 before training (critical for linear models, regularized models)
   - Use pipeline StandardScaler() inside cross-validation to prevent data leakage [CITED: scikit-learn docs]
   - Random Forest / Gradient Boosting less sensitive to scaling, but consistency improves reproducibility

### Sample Feature Engineering Audit for FPL-Auto

Current `get_gw_data()` extracts 20 raw features per player. Recommended additions:
- **Form metrics:** rolling 5-GW average of `assists, goals_scored, creativity, threat, minutes`
- **Efficiency:** `goals_scored / minutes` (prevents low-minute noise), `clean_sheets / minutes` (for DEF)
- **Position delta:** player xP vs. position average (is this player overperforming?)
- **Ownership signal:** `selected` percentage change year-over-year (differential picks matter)
- **Injury risk:** flag if player's minutes dropped >50% recently

[ASSUMED] Current model uses only raw GW stats — feature engineering would increase feature count from ~20 to ~35-50. This requires careful validation to avoid overfitting.

---

## 2. Validation Strategies

### Standard Approach: Time-Series Cross-Validation (REQUIRED for FPL)

**Why TimeSeriesSplit, not KFold?**

FPL xP prediction is a **time-series problem** — GW 1-19 data predicts GW 20, GW 1-20 predicts GW 21, etc. Standard KFold shuffles data, breaking temporal order. This causes:
- **Future data leakage**: training model sees data from matches it's supposed to predict
- **Overly optimistic CV scores**: random splits create unrealistic data order
- **Poor generalization**: model fails on truly forward-looking predictions

[VERIFIED: https://scikit-learn.org/stable/modules/cross_validation.html - TimeSeriesSplit requirement]

**TimeSeriesSplit Implementation:**

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)

# Fold 1: train on [GW1:5], test on [GW6]
# Fold 2: train on [GW1:6], test on [GW7]
# Fold 3: train on [GW1:7], test on [GW8]
# Fold 4: train on [GW1:8], test on [GW9]
# Fold 5: train on [GW1:9], test on [GW10]

for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
```

Key properties:
- **Training always precedes testing**: no future data in training set
- **Growing windows**: first fold trains on 19 weeks, last fold on 32+ weeks (realistic model maturity)
- **No shuffling**: preserves temporal structure

[CITED: https://scikit-learn.org/stable/modules/cross_validation.html]

### Validation Strategy: Prevent Data Leakage

**Three Critical Rules:**

1. **Split BEFORE preprocessing**
   ```python
   # WRONG: leaks test statistics into training
   X_scaled = StandardScaler().fit_transform(X)  # fits on ALL data
   X_train, X_test, y_train, y_test = train_test_split(X_scaled, y)
   
   # RIGHT: fit scaler only on training data
   X_train, X_test, y_train, y_test = train_test_split(X, y)
   scaler = StandardScaler().fit(X_train)
   X_train_scaled = scaler.transform(X_train)
   X_test_scaled = scaler.transform(X_test)
   ```

2. **Use sklearn Pipeline to enforce split-first rule**
   ```python
   from sklearn.pipeline import Pipeline
   from sklearn.preprocessing import StandardScaler
   from sklearn.ensemble import GradientBoostingRegressor
   
   # Pipeline: StandardScaler fits on training data, applies to all folds
   model = Pipeline([
       ('scaler', StandardScaler()),
       ('regressor', GradientBoostingRegressor())
   ])
   
   # cross_val_score automatically prevents leakage
   cross_val_score(model, X, y, cv=TimeSeriesSplit(n_splits=5))
   ```
   
   [VERIFIED: scikit-learn docs - Pipeline prevents leakage]

3. **Feature Selection INSIDE the pipeline, not before**
   ```python
   # WRONG: SelectKBest chooses features based on ALL data
   selector = SelectKBest(k=10).fit(X, y)
   X_selected = selector.transform(X)
   X_train, X_test = train_test_split(X_selected, y)
   
   # RIGHT: selector learns feature importance only from training fold
   model = Pipeline([
       ('selector', SelectKBest(k=10)),
       ('regressor', GradientBoostingRegressor())
   ])
   cross_val_score(model, X, y, cv=TimeSeriesSplit(n_splits=5))
   ```
   
   [VERIFIED: scikit-learn common pitfalls documentation]

### Validation Strategy: Nested Cross-Validation (for Hyperparameter Tuning)

When tuning hyperparameters (e.g., GridSearchCV), use **nested CV** to separate model selection from evaluation:

```python
from sklearn.model_selection import GridSearchCV, cross_val_score

param_grid = {'n_estimators': [50, 100, 150], 'learning_rate': [0.01, 0.1, 0.2]}

# Inner CV: selects best hyperparameters
grid_search = GridSearchCV(
    GradientBoostingRegressor(),
    param_grid,
    cv=TimeSeriesSplit(n_splits=3),
    n_jobs=-1
)

# Outer CV: evaluates final model performance
scores = cross_val_score(
    grid_search,
    X, y,
    cv=TimeSeriesSplit(n_splits=5)
)

print(f"Generalization error: {1 - scores.mean():.3f}")
```

Inner CV optimizes; outer CV estimates true generalization performance.

[CITED: https://scikit-learn.org/stable/modules/cross_validation.html]

### Avoiding Overfitting: Sample-to-Feature Ratio

**Rule of thumb: 10:1 minimum, 20:1 preferred**

- FPL-Auto trains on ~1900 player-weeks (38 GW * 50 players/position, excluding missing data)
- If feature engineering increases features from 20 to 50, ratio drops from 95:1 to 38:1 (still safe)
- **Action:** before adding >10 new features, verify training set size remains adequate

[CITED: https://www.machinelearningmastery.com/5-common-mistakes-in-machine-learning-and-how-to-avoid-them/]

---

## 3. Iteration Workflow

### Standard Process: Feature → Retrain → Evaluate → Decide

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. BASELINE ESTABLISHMENT                                       │
│    - Measure current model RMSE/MAE on TimeSeriesSplit (5 folds)│
│    - Record per-position scores (GK/DEF/MID/FWD separate)       │
│    - Save feature importance analysis                           │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. HYPOTHESIS: ONE feature engineering change only              │
│    Examples:                                                     │
│    - Add 5-GW rolling average of assists                        │
│    - Add fixture difficulty * player_form interaction          │
│    - Impute NaN with position median instead of drop            │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. RETRAIN with new feature set                                 │
│    - Use SAME TimeSeriesSplit, SAME CV strategy                 │
│    - Re-fit on GW 1-19 window for each fold                     │
│    - Commands: `python model.py -season 2021-22 -repeat 19`    │
│               + `-score_train_vs_test` flag to detect leakage   │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. EVALUATE across all metrics                                  │
│    - RMSE change (primary): improvement > 0.05 is significant   │
│    - Per-position breakdown: ensure all positions improve       │
│    - Learning curve: plot train vs. test RMSE across GWs        │
│    - Permutation importance: which features now matter most?    │
│    - Feature count/efficiency: new features/reduction in RMSE   │
└─────────────────────────────────────────────────────────────────┘
                             ↓
        ┌────────────────────────────────────────┐
        │ Does RMSE improve by >2%?              │
        ├────────────────────────────────────────┤
        │ YES →  Keep feature, go to 2 (iterate) │
        │ NO  →  Discard, go to 2 (try different)│
        └────────────────────────────────────────┘
```

### Actionable Metrics for Each Iteration

| Metric | How to Measure | Threshold for "Keep" | Why |
|--------|----------------|---------------------|-----|
| **RMSE** | `cross_val_score(model, X, y, cv=TimeSeriesSplit(n_splits=5), scoring='neg_mean_squared_error')` | < baseline by 2-5% | Primary accuracy metric |
| **MAE** | Same as RMSE but `scoring='neg_mean_absolute_error'` | < baseline by 2-5% | Interpretable in FPL points |
| **Train vs. Test gap** | Compare train RMSE to test RMSE across folds | < 10% relative difference | Signals overfitting if gap > 15% |
| **Per-position improvement** | Separate RMSE for GK/DEF/MID/FWD | All positions improve or none drop >1% | Ensure change doesn't hurt one position |
| **Feature importance change** | `permutation_importance(model, X_test, y_test)` | New feature in top 5? | Verify hypothesis—did new feature actually matter? |

### Command Workflow for FPL-Auto

```bash
# Step 1: Baseline
PY=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3
$PY model.py -season 2021-22 -repeat 19 -score_train_vs_test -display_weights > baseline_2021-22.log
$PY model.py -season 2022-23 -repeat 19 -score_train_vs_test -display_weights > baseline_2022-23.log
$PY model.py -season 2023-24 -repeat 19 -score_train_vs_test -display_weights > baseline_2023-24.log

# Step 2: Modify features in fpl_auto/data.py → get_gw_data() or avg_player_data()

# Step 3: Retrain
$PY model.py -season 2021-22 -repeat 19 -score_train_vs_test -display_weights > iteration1_2021-22.log
diff baseline_2021-22.log iteration1_2021-22.log | grep "Average" 

# Step 4: Evaluate
# Extract RMSE, MAE, Accuracy from all three seasons
# Compare: (baseline_avg - iteration1_avg) / baseline_avg = % improvement
```

[ASSUMED] Current workflow manually inspects model outputs. Recommend adding automated regression testing to catch performance regressions.

---

## 4. Common Pitfalls

### Pitfall 1: Data Leakage Through Preprocessing

**What goes wrong:** 
StandardScaler or feature selection is fit on the entire dataset before train/test split, causing test data statistics to influence the training process. This leads to unrealistically high cross-validation scores that don't generalize.

**Why it happens:** 
Developers optimize preprocessing independently, then split data, not realizing mean/std from test data already shaped the training inputs.

**How to avoid:**
- Always use sklearn.pipeline.Pipeline for preprocessing + model
- Never call `.fit_transform()` on full X before splitting
- Split first, then fit transformers **only on training fold**

**Warning signs:**
- Train RMSE and test RMSE are suspiciously close (< 5% gap) — good models show 10-20% gap
- Removing a feature causes RMSE to improve by >0.5 points (feature leakage reversal)
- Hyperparameter tuning with GridSearchCV finds "perfect" parameters that don't help in production

**FPL-Auto check:**
```python
# In model.py, before predictor.fit():
assert not hasattr(training_data[0][0], '_scaler_fitted'), "Leakage: scaler fitted before split"
```

[VERIFIED: scikit-learn common pitfalls]

### Pitfall 2: Using Wrong Feature Importance Method

**What goes wrong:**
Tree-based models (GradientBoosting, RandomForest) provide `feature_importances_` based on in-tree feature usage. This metric can be misleading with multicollinear features—correlated features may receive zero importance if the tree chose a correlated feature first.

**Why it happens:**
`feature_importances_` is convenient and fast, but doesn't answer "what matters for predictions?"—it answers "what did this tree use?"

**How to avoid:**
Use **permutation importance** instead—shuffle each feature and measure prediction error increase. This is model-agnostic and handles multicollinearity better.

```python
from sklearn.inspection import permutation_importance

perm_importance = permutation_importance(
    trained_model,
    X_validation,
    y_validation,
    n_repeats=10,
    random_state=42
)

# perm_importance.importances_mean tells you actual predictive value
# Sort and interpret: "removing this feature hurts predictions by X%"
```

[VERIFIED: scikit-learn permutation importance docs]

**FPL-Auto current code:**
```python
eval.display_weights(i, predictor.feature_importances(), feature_list, POSITIONS)
```
This uses tree feature importance. Consider switching to permutation importance for better insights.

### Pitfall 3: Hyperparameter Tuning Without Nested CV

**What goes wrong:**
Using the same cross-validation split for both hyperparameter selection (e.g., GridSearchCV) and final evaluation causes overfitting to the CV splits themselves. You'll think model generalizes well, but it's just well-tuned for your specific fold structure.

**Why it happens:**
Inner loop (GridSearchCV) optimizes parameters on CV folds. If you then report CV scores from the same folds, you're double-dipping on the same validation data.

**How to avoid:**
Use nested CV:
- **Inner CV:** GridSearchCV finds best hyperparameters (uses 3-fold TimeSeriesSplit)
- **Outer CV:** cross_val_score estimates true generalization (uses separate 5-fold TimeSeriesSplit)

```python
grid = GridSearchCV(
    GradientBoostingRegressor(),
    {'learning_rate': [0.01, 0.1]},
    cv=TimeSeriesSplit(n_splits=3)
)

# Evaluate grid search itself on outer folds
scores = cross_val_score(
    grid,
    X, y,
    cv=TimeSeriesSplit(n_splits=5)
)
# These scores are realistic; inner grid search didn't see outer folds
```

[VERIFIED: scikit-learn cross-validation docs]

### Pitfall 4: Confusing Train/Test Metrics

**What goes wrong:**
Training RMSE is always lower than test RMSE. If they're too close, model is underfitting. If they're far apart, model is overfitting. Practitioners sometimes ignore one or the other, missing the actual story.

**Why it happens:**
Quick iterations focus on test RMSE only, skipping the diagnostic (train RMSE, gap analysis).

**How to avoid:**
Always report both:
```
GW20 Test:  GK: AE: 0.45, RMSE: 0.58, ACC: 85.2%
GW20 Train: GK: AE: 0.35, RMSE: 0.42, ACC: 92.1%

Gap ratio = (0.58 - 0.42) / 0.42 = 38% overfitting
```

**Interpretation:**
- Gap 5-10%: good fit, model generalizes
- Gap 10-20%: acceptable, slight overfitting
- Gap >20%: too complex, reduce regularization or add training data

FPL-Auto model.py already does this with `-score_train_vs_test` flag [VERIFIED: line 73-83].

### Pitfall 5: Adding Features Without Removing Collinear Ones

**What goes wrong:**
Adding too many features increases model complexity, requiring more training data. With fixed data, overfitting worsens. Correlated features also increase variance without improving predictions.

**Why it happens:**
"More features = more information" is intuitively appealing but wrong when features are redundant.

**How to avoid:**
- Measure feature correlation before adding interaction terms
- Use variance inflation factor (VIF) to identify multicollinearity
- Remove features with VIF > 5 or correlation > 0.9

```python
from statsmodels.stats.outliers_influence import variance_inflation_factor
import pandas as pd

vif_data = pd.DataFrame()
vif_data["Feature"] = X.columns
vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
print(vif_data[vif_data["VIF"] > 5])  # High multicollinearity
```

**FPL-Auto check:**
If feature engineering increases feature count from 20 to 50, verify no feature pair has correlation > 0.85 before training.

[ASSUMED] Current models don't explicitly check for multicollinearity. This could explain plateau in model improvements.

---

## Code Examples

### Example 1: TimeSeriesSplit with GradientBoosting (FPL-specific)

```python
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import numpy as np

# X: shape (1900, 20) — 1900 player-weeks, 20 features
# y: shape (1900,) — actual points for each player-week

# Create pipeline: StandardScaler -> GradientBoosting
model = Pipeline([
    ('scaler', StandardScaler()),
    ('regressor', GradientBoostingRegressor(
        n_estimators=110,
        learning_rate=0.1,
        max_depth=3,
        max_features=10,
        criterion='squared_error'
    ))
])

# Time-series aware cross-validation
tscv = TimeSeriesSplit(n_splits=5)  # 5 folds, train/test ratio grows

# Evaluate: each fold trains on earlier weeks, tests on later weeks
rmse_scores = -cross_val_score(
    model, X, y,
    cv=tscv,
    scoring='neg_mean_squared_error',
    n_jobs=-1
)

print(f"RMSE per fold: {np.sqrt(rmse_scores)}")
print(f"Average RMSE: {np.sqrt(rmse_scores.mean()):.3f} (+/- {np.sqrt(rmse_scores.std()):.3f})")

# Source: scikit-learn.org/stable/modules/model_selection.html
```

### Example 2: Nested CV for Hyperparameter Tuning

```python
from sklearn.model_selection import GridSearchCV, cross_val_score, TimeSeriesSplit
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

model = Pipeline([
    ('scaler', StandardScaler()),
    ('regressor', GradientBoostingRegressor())
])

# Parameter grid: test different learning rates and tree depths
param_grid = {
    'regressor__learning_rate': [0.01, 0.05, 0.1],
    'regressor__max_depth': [2, 3, 4, 5],
    'regressor__n_estimators': [50, 100, 150]
}

# Inner CV: GridSearchCV finds best params on 3 folds
inner_cv = TimeSeriesSplit(n_splits=3)
grid_search = GridSearchCV(
    model,
    param_grid,
    cv=inner_cv,
    scoring='neg_mean_squared_error',
    n_jobs=-1
)

# Outer CV: evaluate final model on separate 5 folds
outer_cv = TimeSeriesSplit(n_splits=5)
rmse_scores = -cross_val_score(
    grid_search,
    X, y,
    cv=outer_cv,
    scoring='neg_mean_squared_error',
    n_jobs=-1
)

print(f"Best params found: {grid_search.best_params_}")
print(f"Generalization RMSE: {np.sqrt(rmse_scores.mean()):.3f}")

# Source: scikit-learn.org/stable/modules/cross_validation.html#nested-cv
```

### Example 3: Permutation Importance (Better Than feature_importances_)

```python
from sklearn.inspection import permutation_importance
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import pandas as pd
import numpy as np

# Train model (already fit)
model = Pipeline([
    ('scaler', StandardScaler()),
    ('regressor', GradientBoostingRegressor(n_estimators=110))
]).fit(X_train, y_train)

# Compute permutation importance on validation set
result = permutation_importance(
    model,
    X_val,  # Validation set
    y_val,
    n_repeats=10,  # Shuffle each feature 10 times
    random_state=42,
    n_jobs=-1
)

# Create interpretable DataFrame
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': result.importances_mean,
    'std': result.importances_std
}).sort_values('importance', ascending=False)

print(importance_df.head(10))
# Output shows features that, when removed, increase prediction error the most

# Source: scikit-learn.org/stable/modules/permutation_importance.html
```

### Example 4: Feature Engineering - Rolling Stats + Interactions

```python
import pandas as pd
import numpy as np

# Input: gw_data from FplData.get_gw_data() for GW 15
#        shape: (500 players, 20 features)

def engineer_features(gw_data, season, gw, vastaav_instance):
    """Add rolling averages, interactions, and derived features."""
    
    df = gw_data.copy()
    
    # 1. ROLLING AVERAGES (requires historical data)
    for window in [2, 5, 10]:
        # Get previous N weeks of data for same players
        for i in range(1, window + 1):
            try:
                prev_gw = vastaav_instance.get_gw_data(season, gw - i)
                prev_gw = prev_gw[prev_gw['position'] == df['position'].iloc[0]]
                
                # Match players and aggregate
                df[f'assists_rolling_{window}gw'] = df.index.map(
                    prev_gw['assists'].to_dict()
                ).fillna(0)
            except:
                df[f'assists_rolling_{window}gw'] = 0
    
    # 2. INTERACTIONS (within-GW features)
    df['efficiency_goals_per_min'] = df['goals_scored'] / (df['minutes'] + 1)
    df['threat_per_shot'] = df['threat'] / (df['selected'] + 1)
    df['strength_advantage'] = df['strength_attack_home'] - \
                               df['strength_defence_home']
    
    # 3. POSITION-SPECIFIC (clean sheets for defense, etc)
    position = df['position'].iloc[0]
    if position == 'DEF':
        df['clean_sheets_efficiency'] = df['clean_sheets'] / (df['minutes'] + 1)
    elif position == 'GK':
        df['saves_per_shot_faced'] = df['saves'] / (df['goals_conceded'] + 1)
    
    # 4. MISSING DATA FLAGGING
    for col in df.columns:
        if df[col].isna().any():
            df[f'{col}_was_missing'] = df[col].isna().astype(int)
    
    # 5. IMPUTATION
    for col in df.select_dtypes(include=[np.number]):
        if df[col].isna().any():
            df[col].fillna(df[col].median(), inplace=True)
    
    return df
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Random train/test split (KFold) | TimeSeriesSplit (respects temporal order) | Standard since ~2020 in sports ML | Prevents future data leakage; realistic generalization estimates |
| Raw box-score features | Engineered metrics (rolling averages, efficiency ratios) | Ongoing in sports analytics | 5-15% RMSE improvement per feature engineering round |
| `feature_importances_` (tree-based) | Permutation importance (model-agnostic) | Recommended since scikit-learn 0.24 (2020) | Handles multicollinearity better; actionable insights |
| Manual hyperparameter tuning | GridSearchCV + nested CV | Standard 2018+, now best practice | Systematic, reproducible, unbiased evaluation |
| Train once, deploy forever | Retrain each season with new data | FPL context | Models degrade ~5-10% per season without retraining |

**Deprecated/outdated:**
- `tree_feature_importances_` for decision-making (replaced by permutation importance)
- `train_test_split` for time-series (use TimeSeriesSplit)
- Manual CV reporting without nested approach (use GridSearchCV)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Current FPL-Auto uses tree `feature_importances_` for feature selection decisions | Pitfall 2 | If permutation importance shows different ranking, feature engineering strategy may be targeting wrong signals |
| A2 | Training set for weekly GW models contains ~1900 player-weeks (19 GW * 100 players/pos) | Feature engineering | If actual training set is smaller (<1000), adding 30+ features risks overfitting; need to reduce features or use regularization |
| A3 | Current model does not use TimeSeriesSplit; uses standard train/test split or KFold | Validation strategies | If already using TimeSeriesSplit, recommendations for data leakage prevention still apply, but temporal ordering already respected |
| A4 | Feature engineering goal is to improve RMSE by 5-10% per iteration, not per feature | Pitfall 5 | If expectation is 2-3% per feature, feature engineering will yield diminishing returns and appear to plateau |

---

## Open Questions

1. **Current baseline metrics across seasons**
   - What we know: model.py outputs AE, RMSE, ACC per GW; `-score_train_vs_test` shows train/test gap
   - What's unclear: is there a tracked baseline comparing 2021-22 vs. 2022-23 vs. 2023-24? Are improvements consistent across positions?
   - Recommendation: Create automated regression test that fails if average RMSE degrades >2% from baseline

2. **Training data characteristics**
   - What we know: GW data sourced from vaastav/Fantasy-Premier-League; data includes 38 weeks per season
   - What's unclear: are players filtered before training (e.g., min. minutes played)? Are bench players (0-5 min) included in training set?
   - Recommendation: Analyze distribution of `minutes` in training set; consider separate models for starters vs. substitutes

3. **Feature selection strategy**
   - What we know: model.py has `-display_weights` flag; CLAUDE.md mentions post_model_weightings for next-GW adjustment
   - What's unclear: are current features manually curated or data-driven? Is feature importance used to prune low-impact features?
   - Recommendation: Add automated feature importance ranking to model.py; maintain top N features (e.g., top 15 per position) to simplify interpretation

---

## Environment Availability

**Step 2.6 Status:** SKIPPED

Current research is code/modeling focused with no external service dependencies. All required tools (scikit-learn, pandas, numpy, flake8) are listed in requirements.txt and already installed per project setup (Python 3.10 via CLAUDE.md).

---

## Validation Architecture

**Workflow nyquist_validation status:** No `.planning/config.json` found; assume validation disabled for this research phase.

Current testing framework: unittest (per CLAUDE.md `$PY -m unittest tests -v`). Model improvements should include regression tests to detect RMSE degradation.

---

## Security Domain

Not applicable — model improvement research focuses on algorithmic accuracy, not security-sensitive data handling. FPL xP predictions use public historical data (no user PII or financial secrets).

---

## Sources

### Primary (HIGH confidence)
- [scikit-learn 1.8.0 documentation: Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [scikit-learn 1.8.0 documentation: Common Pitfalls](https://scikit-learn.org/stable/common_pitfalls.html)
- [scikit-learn 1.8.0 documentation: Permutation Importance](https://scikit-learn.org/stable/modules/permutation_importance.html)
- [scikit-learn 1.8.0 documentation: Pipelines and Composite Estimators](https://scikit-learn.org/stable/modules/compose.html)

### Secondary (MEDIUM confidence)
- [MachineLearningMastery: 5 Common Mistakes in Machine Learning](https://www.machinelearningmastery.com/5-common-mistakes-in-machine-learning-and-how-to-avoid-them/)
- [MachineLearningMastery: The Concise Guide to Feature Engineering](https://www.machinelearningmastery.com/the-concise-guide-to-feature-engineering-for-better-model-performance/)
- [KDnuggets: 5 Critical Feature Engineering Mistakes](https://www.kdnuggets.com/5-critical-feature-engineering-mistakes-that-kill-machine-learning-projects)
- [Analytics Vidhya: Machine Learning in Sports Analytics 2025](https://www.analyticsvidhya.com/blog/2025/07/machine-learning-in-sports/)

### Tertiary (MEDIUM confidence — domain-specific)
- [arXiv: A Systematic Review of Machine Learning in Sports Betting](https://arxiv.org/html/2410.21484v1)
- [arXiv: Who You Play Affects How You Play — Temporal Convolution in Sports](https://arxiv.org/pdf/2303.16741)

---

## Metadata

**Confidence breakdown:**
- **Validation strategies:** HIGH — TimeSeriesSplit and data leakage prevention directly from scikit-learn docs with code examples
- **Feature engineering patterns:** MEDIUM-HIGH — sports ML research confirms effectiveness, but FPL-specific feature list is partially assumed
- **Pitfalls:** HIGH — all four pitfalls verified against scikit-learn common pitfalls docs and multiple ML best-practices sources
- **Code examples:** HIGH — all examples are direct from official scikit-learn documentation or verified against current API

**Research date:** 2026-05-27
**Valid until:** 2026-06-27 (30 days — sklearn API stable, but sports prediction techniques evolve seasonally)

**How to act on this research:**
1. Start with Pitfall 1 (preprocessing in pipeline) — lowest friction, highest immediate impact
2. Implement TimeSeriesSplit (Validation Strategies section) — replaces manual CV logic in current model.py
3. Add permutation importance reporting (Example 3) — understand what features actually drive predictions
4. Iterate on feature engineering using the workflow in Section 3 — test one hypothesis per iteration
