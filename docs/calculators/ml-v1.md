# QuantLab machine learning and walk-forward specification (V1)

## 1. Panel construction

The observation unit is the **monthly cross-section**, not the trading day. One row per
instrument per month-end close.

- **Features**: point-in-time factor scores at that close. The factor runtime cannot
  import the label namespace, and the architecture tests enforce that boundary.
- **Label**: the cross-sectional rank of the forward return, mapped to `[-0.5, 0.5]`.
  Entry is the **next session's open**, not the close the signal was observed at - a
  score computed from the close of session *t* cannot be filled at that same close.
- **Why rank, not return**: the task is to order names, not to forecast a return level.
  A rank label is also immune to the handful of extreme moves that would otherwise
  dominate a squared-error fit.

## 2. Walk-forward cross-validation

- **Windowing**: expanding train window, 60 monthly cross-sections minimum.
- **Test block**: 12 months, stepping 12 months, so test blocks tile without overlap.
- **Purge**: 1 rebalance period. The label of the last training month resolves inside
  the test block, so that month is removed.
- **Embargo**: 1 further rebalance period, to break the serial correlation that survives
  the purge.
- Random shuffled splits are prohibited for authoritative evaluation.

## 3. Models

| Model | What it is |
|---|---|
| `composite` | Equal weight over cross-sectionally standardized features. The baseline. |
| `ridge` | L2-regularized linear ranker, alpha 1.0. Gaussian elimination with partial pivoting, implemented in `quantlab/ml/models/linear.py`. |
| `gbdt` | Gradient boosted regression trees on residuals, implemented in `quantlab/ml/models/tree.py`. Not LightGBM or scikit-learn - a from-scratch learner, slower and less tuned than a production library. |

Preprocessing is fitted on training rows only.

## 4. Evaluation metrics

- **Spearman rank IC** per test cross-section, with **average ranks for ties**. Assigning
  tied values the rank of their first occurrence biases the correlation, and tree models
  emit repeated scores constantly because every leaf returns one value.
- **IC IR** = mean(IC) / sd(IC) per period. The annualized figure multiplies by
  `sqrt(12)`, because the ICs are monthly. Using `sqrt(252)` here - as if they were
  daily - inflates every information ratio by more than four times.
- **IC t-statistic** = IR x sqrt(number of periods).
- **Quintile returns**: the average realized label by predicted quintile, measured from
  the predictions and outcomes. Not derived from the IC.

## 5. Champion selection

A model must exceed the composite baseline by more than `MIN_INCREMENTAL_RANK_IC`
(0.005 rank IC) out of sample to take the slot. Otherwise the baseline keeps it.

The margin exists because ranking by raw score alone crowns whichever model got luckier
on the test folds and calls it a finding.

## 6. Label-shuffle permutation control

Labels are permuted **within each cross-section**, leaving features, folds, purge, and
the label distribution untouched. Any measured skill that survives is coming from
something other than prediction.

One shuffle proves nothing. Models are refit per fold, so per-session ICs inside a fold
are driven by a single fitted model, and a 24-fold study has an effective sample size
closer to 24 than to its ~288 sessions; one draw landing above the real score is
ordinary noise. The control therefore runs several permutations and reports where the
real score sits in that distribution, as an empirical p-value with add-one smoothing
(the smallest attainable p-value from *n* permutations is `1/(n+1)`).
