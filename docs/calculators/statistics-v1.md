# QuantLab Statistical Diagnostics Specifications (V1)

## 1. Stationary Block Bootstrap
- **Method**: Politis & Romano (1994) Stationary Block Bootstrap.
- **Block Length**: Expected length $L = 21$ trading sessions (geometric block distribution).
- **Quantiles**: Empirical percentile bootstrap confidence intervals ($2.5\%$ and $97.5\%$).

## 2. Deflated Sharpe Ratio (DSR)
- **Method**: Bailey & Lopez de Prado (2014).
- **Expected Max Sharpe**:
  $$E[\max_N] \approx \sqrt{V[\{SR_n\}]} \left( (1 - \gamma) Z^{-1}(1 - 1/N) + \gamma Z^{-1}(1 - 1/(N \cdot e)) \right)$$
  where $\gamma \approx 0.5772156649$ (Euler-Mascheroni constant).
- **Standard Error under Non-Normality**:
  $$\sigma_{SR} = \sqrt{\frac{1 - S \cdot SR + \frac{K - 1}{4} SR^2}{T - 1}}$$
- **DSR Statistic**:
  $$\text{DSR} = \Phi\left( \frac{SR - E[\max_N]}{\sigma_{SR}} \right)$$

### Units matter here

$SR$ is the **per-period** Sharpe and $T$ is the sample length in those same periods.
Passing an annualized Sharpe alongside a daily $T$ inflates the statistic by roughly the
annualization factor and makes almost any strategy significant. `TrialDiagnostics.evaluate`
therefore takes the return series itself rather than a pre-computed Sharpe.

$S$ (skewness) and $K$ (kurtosis) are **estimated from the realized series**, not assumed
normal. Correcting for fat tails and negative skew is the entire reason the deflated
statistic exists: a strategy that earns steadily and then gaps down is exactly the case a
normal assumption waves through.

### What the trial count means

$N$ is the number of trials **recorded in this run's ledger**, not an imagined search
budget. Every parameter sweep point and factor ablation the validation run performs is
counted. With a single recorded trial there is no measured spread of Sharpes to deflate
against, and the result leans on an assumed variance of $0.25$ - a stated assumption
rather than a measurement.

## 3. Newey-West t-statistic

Overlapping forward-return windows make consecutive ICs serially correlated, so the plain
OLS t-statistic overstates significance. The reported IC t-statistic widens the standard
error by the autocovariance the overlap induces, using a Bartlett kernel with 3 lags:

$$\hat{\sigma}^2 = \gamma_0 + 2\sum_{\ell=1}^{L}\left(1 - \frac{\ell}{L+1}\right)\gamma_\ell$$

## 4. False Discovery Rate (FDR)
- **Method**: Benjamini & Hochberg (1995).
- **Procedure**: Sort $p_{(1)} \le \dots \le p_{(M)}$. Find largest $k$ such that $p_{(k)} \le \frac{k}{M} \alpha$. Reject null for all $i \le k$.
