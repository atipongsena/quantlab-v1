# QuantLab Machine Learning & Walk-Forward Specifications (V1)

## 1. Walk-Forward Cross-Validation
- **Windowing**: Expanding or Rolling train window.
- **Purging**: Embargo/Purge gap $P \ge \text{Label Horizon}$ ($21$ sessions) between train end and test start.
- **Embargoing**: $E = 5$ sessions post-test embargo to prevent auto-correlation leakage.

## 2. Models
- **Baseline Heuristic Composite**: Fixed parameter-free linear combination of normalized factor scores.
- **Ridge Regressor**: Deterministic $L_2$-regularized linear cross-sectional ranker ($\alpha = 1.0$).
- **LightGBM-Style Ranker**: Gradient boosted regression trees optimizing MSE loss on residuals.

## 3. Evaluation Metrics
- **Spearman Rank IC**: Cross-sectional correlation between predictions $\hat{y}_t$ and forward excess returns $y_t$.
- **Information Ratio (IR)**: Annualized consistency $\text{IR} = \frac{\mu_{\text{IC}}}{\sigma_{\text{IC}}} \sqrt{252}$.
- **Quintile Monotonicity**: Strict monotonic progression $Q_1 \le Q_2 \le Q_3 \le Q_4 \le Q_5$.

## 4. Champion Selection Protocol
- ML models must exceed heuristic composite Rank IC by $> 0.005$ out-of-sample to earn Champion status.
- Otherwise, the simple heuristic composite remains Champion to protect against model overfitting and complexity theater.
