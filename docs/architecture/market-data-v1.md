# Market data pipeline and its limits

## What the fixture stores

`scripts/download_real_market_data.py` writes four files per universe:

| File | Contents |
|---|---|
| `listings.csv` | Symbol, exchange, sector, first observed session |
| `prices.csv` | **As-traded** daily OHLCV |
| `actions.csv` | Real split and dividend history from the provider |
| `reference_adjusted_close.csv` | The provider's own total-return series, for cross-checking |

`download_manifest.json` records the SHA-256, byte count, and row count of each file
plus per-instrument coverage, so a later download can be checked against the run a
result was produced from.

## The un-adjustment step

Yahoo's `Close` column is **already split-adjusted**, even with `auto_adjust=False`. On
2020-08-31 AAPL shows $129.04, not the $499 it actually traded at before the 4:1 split.

Writing that out as a raw price *and* recording the split as a corporate action makes the
engine apply the same split twice. Every price before the split ends up a quarter of what
it should be, every return through that window is wrong, and nothing raises.

So the download reverses the provider's split adjustment to recover as-traded prices: a
bar on date *t* is multiplied by the product of every split effective after *t*.
Dividend amounts get the same treatment, because Yahoo quotes those in post-split terms
too - a $0.50 dividend paid before a 4:1 split, divided against an as-traded price four
times larger, shrinks the dividend adjustment to a quarter of its true size.

## The verification that makes this checkable

`scripts/verify_market_data.py` re-derives the total-return series from raw price plus
actions using the engine's own `apply_adjustments`, and compares it against the
provider's independently computed `Adj Close`.

Both series are only defined up to a scale factor, since a backward adjustment anchors on
the final bar, so the comparison normalizes on the last common session first.

This is the check that makes the rest of the research trustworthy. A factor library can
look statistically healthy while silently running on double-adjusted or unadjusted
prices, and nothing downstream would notice.

## Price semantics

| Semantic | Used for |
|---|---|
| `RAW` | Execution, fills, cash accounting. Dividends arrive separately as cash. |
| `TOTAL_RETURN_ADJUSTED` | Return and factor research only. |

Only `RAW` is persisted. Adjusted series are derived on read by `PointInTimeDataFacade`,
which applies solely the actions known as of the query time. A materialized adjusted copy
would be a second source of truth that is not point-in-time, and it would drift.

Mixing the two in one accounting path double-counts dividends.

## Known limitations

**Survivorship bias is present.** Free data providers do not carry delisted price history,
so every name in `configs/universes/us-research-v1.yaml` is one that is still listed
today. Companies that failed or were acquired during the study window are absent, which
biases realized returns upward. Any backtest on this universe inherits that bias, and the
universe config states it in a machine-readable field rather than a footnote.

The synthetic fixture is the one that exercises delisting, mergers, ticker changes, and
restatements - `data/fixtures/synthetic_v1` carries a `DELIST_CORP` that stops trading, an
`FB -> META` rename, a missing-open session, and a restated filing.

**No point-in-time fundamentals on the real-data track.** There is no free source of
as-reported filing history with reliable `available_at` timestamps, so the real-data
track covers price-based factors only. `configs/factors/composite-price-v1.yaml` says so
in its description rather than quietly reweighting a fundamental composite down to its
momentum leg. Fundamental factors run against the synthetic fixture, where the
dual-timestamp semantics are exercised deliberately.

**Provider revisions are not tracked.** A re-download can differ from the recorded
manifest. That is what the SHA-256 in `download_manifest.json` is for: it makes the
difference visible instead of silent.
