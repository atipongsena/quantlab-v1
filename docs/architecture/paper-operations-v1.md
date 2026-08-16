# QuantLab Paper Trading & Daily Operations Specifications (V1)

## 1. Daily Operational Lifecycle
1. **Pre-Market Ingestion**: Ingest latest session bar data into immutable DuckDB store.
2. **Signal & Portfolio Rebalance**: Compute point-in-time cross-sectional alpha, solve portfolio targets, and generate rebalance orders (SELLs before BUYs).
3. **Execution Routing**: Transmit orders to mock broker or paper broker adapter with deterministic slippage and commissions.
4. **Fills & Ledger Update**: Record fills into SQLite state store, updating cash balance and instrument position holdings.
5. **End-of-Day Shadow Reconciliation**: Verify internal shadow ledger against broker reported account. Detect cash mismatches or position breaks.

## 2. Disaster Recovery Protocol
- In the event of system restart or database corruption, state is deterministically reconstructed by replaying the immutable `paper_fills` event stream from initial capital.
