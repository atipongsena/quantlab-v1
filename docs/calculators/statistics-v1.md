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

## 3. False Discovery Rate (FDR)
- **Method**: Benjamini & Hochberg (1995).
- **Procedure**: Sort $p_{(1)} \le \dots \le p_{(M)}$. Find largest $k$ such that $p_{(k)} \le \frac{k}{M} \alpha$. Reject null for all $i \le k$.
