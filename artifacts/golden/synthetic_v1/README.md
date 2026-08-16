# Synthetic V1 Golden Fixture Specification

This directory holds the golden baseline definitions and expectations for the `synthetic_v1` dataset.

## Dataset Structure
- `source/listings.csv`: Historical listing master with common equity, delisting, ETF flags, and ticker changes (`FB` -> `META`).
- `source/prices.csv`: Point-in-time daily bars with volume, split adjustments, and canary missing-open session (`2021-06-15`).
- `source/actions.csv`: Corporate actions containing cash dividends, stock splits (AAPL 4:1), symbol changes, and delistings.
- `source/fundamentals.csv`: Point-in-time financial statements with availability timestamps (`available_at`) and restatement canary on 2020-03-01.

## Temporal Canaries
1. **2020-03-01 Restatement Canary**:
   - `2020-02-19`: Filing not yet available (`available_at = 2020-02-20`).
   - `2020-03-01`: Sees original filing ($22.0B net income).
   - `2020-05-01`: Sees restated filing ($21.5B net income, filed 2020-04-15).
2. **Missing Open Canary**: `2021-06-15` AAPL bar has missing open price.
3. **Rename Invariance**: `FB` becomes `META` on `2022-06-09` without creating fake buy/sell trades or resetting InstrumentId.
4. **Delisting Handling**: `DELIST_CORP` delisted on `2021-12-31`.
