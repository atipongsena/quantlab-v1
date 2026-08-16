# QuantLab V1 Factor Catalog

This document specifies the authoritative mathematical definitions, inputs, lookback periods, availability lags, and missingness policies for all 14 standard factors in QuantLab V1.

---

## 1. Momentum Family

### 1.1 `momentum_12_1` (12M-1M Momentum)
- **Category:** `momentum`
- **Formula:** `(close[-21] / close[-252]) - 1.0`
- **Direction:** `+1` (higher momentum is favored)
- **Lookback:** 252 trading sessions (skipping the most recent 21-session reversal window)
- **Price Semantic:** `total_return` (split and dividend adjusted)
- **Availability Lag:** 0 sessions (available at market close)
- **Missingness Policy:** `insufficient_history` if `< 252` valid bars available

### 1.2 `momentum_6_1` (6M-1M Momentum)
- **Category:** `momentum`
- **Formula:** `(close[-21] / close[-126]) - 1.0`
- **Direction:** `+1`
- **Lookback:** 126 trading sessions (skipping 21 sessions)
- **Price Semantic:** `total_return`
- **Availability Lag:** 0 sessions
- **Missingness Policy:** `insufficient_history` if `< 126` valid bars available

---

## 2. Value Family

### 2.1 `earnings_yield`
- **Category:** `value`
- **Formula:** `net_income / close`
- **Direction:** `+1` (higher earnings yield is favored)
- **Inputs:** PIT fundamentals (`net_income`), market close price
- **Availability Lag:** 1 session after public SEC filing availability
- **Missingness Policy:** `missing_fundamental`

### 2.2 `book_to_market`
- **Category:** `value`
- **Formula:** `stockholders_equity / close`
- **Direction:** `+1`
- **Inputs:** PIT fundamentals (`stockholders_equity`), market close price
- **Availability Lag:** 1 session
- **Missingness Policy:** `missing_fundamental`

### 2.3 `fcf_yield`
- **Category:** `value`
- **Formula:** `free_cash_flow / close`
- **Direction:** `+1`
- **Inputs:** PIT fundamentals (`free_cash_flow`), market close price
- **Availability Lag:** 1 session
- **Missingness Policy:** `missing_fundamental`

---

## 3. Quality Family

### 3.1 `roe` (Return on Equity)
- **Category:** `quality`
- **Formula:** `net_income / stockholders_equity`
- **Direction:** `+1`
- **Availability Lag:** 1 session
- **Missingness Policy:** `missing_fundamental`

### 3.2 `roa` (Return on Assets)
- **Category:** `quality`
- **Formula:** `net_income / total_assets`
- **Direction:** `+1`
- **Availability Lag:** 1 session
- **Missingness Policy:** `missing_fundamental`

### 3.3 `gross_profitability`
- **Category:** `quality`
- **Formula:** `gross_profit / total_assets`
- **Direction:** `+1`
- **Availability Lag:** 1 session
- **Missingness Policy:** `missing_fundamental`

### 3.4 `accrual_quality`
- **Category:** `quality`
- **Formula:** `-(operating_income - operating_cash_flow) / total_assets`
- **Direction:** `+1` (lower accruals yields higher score)
- **Availability Lag:** 1 session
- **Missingness Policy:** `missing_fundamental`

---

## 4. Growth Family

### 4.1 `revenue_growth`
- **Category:** `growth`
- **Formula:** `(revenue[t] - revenue[t-1Y]) / abs(revenue[t-1Y])`
- **Direction:** `+1`
- **Availability Lag:** 1 session
- **Missingness Policy:** `missing_fundamental`

### 4.2 `operating_income_growth`
- **Category:** `growth`
- **Formula:** `(operating_income[t] - operating_income[t-1Y]) / abs(operating_income[t-1Y])`
- **Direction:** `+1`
- **Availability Lag:** 1 session
- **Missingness Policy:** `missing_fundamental`

---

## 5. Risk / Volatility Family

### 5.1 `volatility_60d`
- **Category:** `risk`
- **Formula:** `std(returns[-60:]) * sqrt(252)`
- **Direction:** `-1` (lower volatility yields higher composite score)
- **Lookback:** 60 trading sessions
- **Price Semantic:** `total_return`
- **Missingness Policy:** `insufficient_history`

### 5.2 `max_drawdown_252d`
- **Category:** `risk`
- **Formula:** `max_drawdown(prices[-252:])`
- **Direction:** `-1` (lower drawdown yields higher composite score)
- **Lookback:** 252 trading sessions
- **Price Semantic:** `total_return`
- **Missingness Policy:** `insufficient_history`

### 5.3 `beta`
- **Category:** `risk`
- **Formula:** `cov(r_i, r_m) / var(r_m)`
- **Direction:** `-1` (low-beta anomaly)
- **Lookback:** 252 trading sessions
- **Price Semantic:** `total_return`
- **Missingness Policy:** `insufficient_history`
