# QuantLab Performance Calculator Specifications (V1)

## Performance & Risk Metrics Formulas

1. **Total Return**:
   $$R_{\text{total}} = \frac{V_{\text{final}} - V_{\text{initial}}}{V_{\text{initial}}}$$

2. **Compound Annual Growth Rate (CAGR)**:
   $$\text{CAGR} = (1 + R_{\text{total}})^{\frac{252}{N}} - 1$$

3. **Annualized Volatility**:
   $$\sigma_{\text{ann}} = \sigma_{\text{daily}} \times \sqrt{252}$$

4. **Sharpe Ratio**:
   $$\text{Sharpe} = \frac{\text{CAGR} - r_f}{\sigma_{\text{ann}}}$$

5. **Sortino Ratio**:
   $$\text{Sortino} = \frac{\text{CAGR} - r_f}{\sigma_{\text{downside}} \times \sqrt{252}}$$

6. **Maximum Drawdown (MDD)**:
   $$\text{MDD} = \max_{t} \left( \frac{\text{Peak}_t - V_t}{\text{Peak}_t} \right)$$

7. **Calmar Ratio**:
   $$\text{Calmar} = \frac{\text{CAGR}}{|\text{MDD}|}$$

8. **Win Rate**:
   $$\text{Win Rate} = \frac{N_{\text{positive sessions}}}{N_{\text{total sessions}}}$$

9. **Profit Factor**:
   $$\text{Profit Factor} = \frac{\sum \text{Gains}}{|\sum \text{Losses}|}$$

## Benchmark-relative metrics

A headline CAGR means nothing on its own. Over a rising market, a strategy with beta 1.3
has to clear 1.3x the market's return before any of it counts as skill, so the backtest
report also carries:

10. **Beta** to the benchmark's daily total return:
    $$\beta = \frac{\text{Cov}(r_p, r_b)}{\text{Var}(r_b)}$$

11. **Jensen's alpha**, annualized. This is the intercept, not the raw return difference:
    $$\alpha_{\text{ann}} = \left( \bar{r_p} - \beta \bar{r_b} \right) \times 252$$

12. **Tracking error**:
    $$\text{TE} = \sigma(r_p - r_b) \times \sqrt{252}$$

13. **Information ratio**:
    $$\text{IR} = \frac{\overline{(r_p - r_b)} \times 252}{\text{TE}}$$

The benchmark is read on **total-return adjusted** prices, because a buy-and-hold holder
receives the dividends. Comparing against a price-only index hands the strategy roughly
two points a year of free outperformance.
