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
