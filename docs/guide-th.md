# คู่มือ QuantLab (ภาษาไทย)

เอกสารนี้อธิบายว่าโปรเจคนี้คืออะไร ใช้ทำอะไร ใช้เทคนิคอะไร ทดสอบอย่างไร และต่อยอดต่อได้ทางไหน
ถ้าต้องการดูตัวเลขผลลัพธ์พร้อมรูป ให้ดูที่ [README.md](../README.md)

---

## 1. โปรเจคนี้คืออะไร

QuantLab เป็น **โครงสร้างพื้นฐานสำหรับงานวิจัยเชิงปริมาณ (quantitative research infrastructure)**
บนหุ้นสหรัฐฯ ไม่ใช่ระบบเทรด ไม่ใช่คำแนะนำการลงทุน

หน้าที่ของมันคือทำให้กระบวนการวิจัยกลยุทธ์ **ทำซ้ำได้ ตรวจสอบได้ และถูกหักล้างได้**
ตั้งแต่การนำเข้าข้อมูลราคา ไปจนถึงการตัดสินว่ากลยุทธ์ที่ได้นั้นควรเชื่อหรือไม่

จุดที่ต่างจาก backtest framework ทั่วไปคือ **ชั้นสุดท้ายของระบบมีหน้าที่ปฏิเสธกลยุทธ์**
ไม่ใช่ยืนยันว่ามันดี ระบบจะพยายามหาเหตุผลที่จะไม่เชื่อผลลัพธ์ก่อน แล้วค่อยยอมรับ

### ใช้ทำอะไรได้บ้าง

| งาน | คำสั่ง |
|---|---|
| นำเข้าข้อมูลราคาพร้อม corporate action | `quantlab dataset build` |
| ทดสอบว่าปัจจัย (factor) ทำนายผลตอบแทนได้จริงไหม | `quantlab factor research` |
| จำลองการเทรดจริงพร้อมบัญชี ค่าคอม slippage | `quantlab backtest run` |
| เทียบโมเดล ML กับ baseline แบบไม่มี lookahead | `quantlab model compare` |
| ตรวจสอบว่ากลยุทธ์รอดจากการพยายามหักล้างไหม | `quantlab validate run` |
| จำลอง paper trading + กู้คืนสถานะจาก ledger | `quantlab paper simulate` |

---

## 2. ปัญหาที่ระบบนี้ตั้งใจแก้

งานวิจัยเชิงปริมาณล้มเหลวได้หลายทาง และเกือบทุกทาง **ไม่มีอะไรฟ้อง** ผลลัพธ์จะยังดูสมเหตุสมผล

| ปัญหา | ผลที่เกิด | สิ่งที่ระบบทำ |
|---|---|---|
| **Lookahead bias** | ใช้ข้อมูลที่ยังไม่รู้ ณ เวลานั้น ผลเลยดีเกินจริง | ทุก query กรอง `observed_at <= as_of` และปรับราคาด้วย corporate action ที่รู้แล้วเท่านั้น |
| **Corporate action ผิด** | split/dividend ปรับผิด ทำให้ผลตอบแทนเพี้ยนทั้งชุด | ตรวจสอบกับ series ของ provider แบบอิสระ (101/101 ผ่าน) |
| **Survivorship bias** | ใช้เฉพาะบริษัทที่รอดมาถึงวันนี้ ผลตอบแทนสูงเกินจริง | ประกาศไว้ชัดเจนใน config แบบ machine-readable + ใช้ synthetic fixture ทดสอบ delisting |
| **Overfitting / data mining** | ลองเยอะแล้วเลือกอันที่ดีที่สุดมารายงาน | นับ trial ทุกครั้งที่รัน แล้วหักด้วย Deflated Sharpe |
| **Multiple testing** | ยิ่งลองเยอะ ยิ่งเจอผลดีโดยบังเอิญ | Deflated Sharpe + FDR |
| **ต้นทุนไม่สมจริง** | edge หายหมดเมื่อคิดค่าธรรมเนียม | มี slippage / commission / volume participation และมี cost sweep |

---

## 3. สถาปัตยกรรม

### การแบ่งชั้น (dependency ชี้เข้าด้านใน)

```
apps/          CLI, REST API, Next.js dashboard, MCP server
   ↓
application/   service ที่ประสานงาน (dataset, factor, backtest, validation, model, paper)
   ↓
quant modules/ factors, backtest, ml, validation, portfolio, paper, analytics
   ↓
domain/        contract ที่ไม่มี dependency ภายนอกเลย (identity, market, orders, portfolio)
```

`quantlab/domain` ห้าม import อะไรที่อยู่ชั้นนอก มีเทสต์บังคับไว้ที่ `tests/architecture/`

### ขนาดโค้ดจริง

| โมดูล | ไฟล์ | บรรทัด | หน้าที่ |
|---|---|---|---|
| `factors/` | 17 | 2,461 | คลัง factor, transform, การประเมิน |
| `application/` | 10 | 2,288 | service ที่ประสานทุกอย่าง |
| `data/` | 13 | 1,959 | PIT store, corporate action, dataset |
| `validation/` | 20 | 1,507 | gate, robustness, สถิติ, red team |
| `backtest/` | 15 | 1,254 | engine, บัญชี, order, ต้นทุน |
| `infrastructure/` | 9 | 979 | partition store, DB, artifact |
| `portfolio/` | 8 | 842 | คัดเลือก, ถ่วงน้ำหนัก, ความเสี่ยง |
| `paper/` | 8 | 738 | paper broker, กระทบยอด, กู้คืน |
| `ml/` | 9 | 727 | panel, walk-forward, โมเดล |
| `domain/` | 11 | 673 | contract หลัก |

### ไหลของข้อมูล

```
CSV จาก provider
   ↓  quantlab dataset build
PIT store (RAW bars อย่างเดียว) + corporate actions ใน SQLite
   ↓  อ่านผ่าน PointInTimeDataFacade (ปรับราคาตอนอ่าน)
factor snapshot → forward return → ประเมิน / backtest / ML panel
   ↓
falsification gates
   ↓
artifact ที่มี hash → REST API → dashboard / MCP
```

**หลักสำคัญ:** เก็บเฉพาะราคาดิบ (RAW) ราคาที่ปรับแล้วคำนวณตอนอ่านเสมอ
ถ้าเก็บราคาปรับแล้วไว้ด้วย มันจะกลายเป็น "แหล่งความจริงที่สอง" ที่ไม่เป็น point-in-time และจะเพี้ยนจากกันในที่สุด

---

## 4. ส่วนประกอบทีละส่วน

### 4.1 Point-in-time data store

**หน้าที่:** เก็บราคาและ corporate action โดยที่ query ณ วันไหน จะเห็นเฉพาะข้อมูลที่รู้ ณ วันนั้น

- **ราคา RAW** = ราคาที่ซื้อขายจริง ใช้สำหรับ execution และบัญชี เงินปันผลเข้ามาเป็นเงินสดแยกต่างหาก
- **ราคา TOTAL_RETURN_ADJUSTED** = ปรับ split + dividend ใช้สำหรับงานวิจัยผลตอบแทนเท่านั้น
- ห้ามใช้ปนกันในเส้นทางบัญชีเดียวกัน เพราะจะนับเงินปันผลซ้ำสองรอบ

Partition ตั้งชื่อเป็น `{instrument}_{semantic}_{year}` และอยู่ใน namespace แยกตาม dataset
เหตุผล: `instrument_id` มาจาก symbol ดังนั้น AAPL ใน dataset A กับ B จะเป็น id เดียวกัน
ถ้าใช้ namespace เดียวกัน dataset ที่สร้างทีหลังจะเขียนทับราคาของอันแรก

### 4.2 Factor library

14 factor แบ่งเป็น 5 กลุ่ม

| กลุ่ม | factor | สูตร | ทิศทาง |
|---|---|---|---|
| Momentum | `momentum_12_1` | `close[-21] / close[-252] - 1` | +1 |
| | `momentum_6_1` | `close[-21] / close[-126] - 1` | +1 |
| Value | `earnings_yield` | `net_income / close` | +1 |
| | `book_to_market` | `stockholders_equity / close` | +1 |
| | `fcf_yield` | `free_cash_flow / close` | +1 |
| Quality | `roe` | `net_income / stockholders_equity` | +1 |
| | `roa` | `net_income / total_assets` | +1 |
| | `gross_profitability` | `gross_profit / total_assets` | +1 |
| | `accrual_quality` | `-(op_income - op_cash_flow) / total_assets` | +1 |
| Growth | `revenue_growth` | YoY | +1 |
| | `operating_income_growth` | YoY | +1 |
| Risk | `volatility_60d` | `std(returns[-60:]) * sqrt(252)` | −1 |
| | `max_drawdown_252d` | `max_drawdown(prices[-252:])` | −1 |
| | `beta` | `cov(r_i, r_m) / var(r_m)` | −1 |

ทิศทาง −1 หมายถึงค่าน้อยดีกว่า ระบบจะกลับเครื่องหมายให้อัตโนมัติ เพื่อให้ "คะแนนสูง = น่าสนใจกว่า" เสมอ

**การจัดการค่าที่หายไป** ไม่ใช้ `fillna(0)` แต่ระบุเหตุผลชัดเจน:
`insufficient_history`, `missing_fundamental`, `invalid_denominator`, `stale_data`
เพราะ "ไม่มีข้อมูล" กับ "ค่าเป็นศูนย์" คนละเรื่องกัน และการเติมศูนย์จะทำให้หุ้นที่ไม่มีข้อมูลไปกองอยู่กลาง cross-section

### 4.3 Backtest engine

Event loop แบบ discrete ลำดับเหตุการณ์ในหนึ่งวัน:

```
MarketOpen   → ใช้ corporate action ก่อน → ส่งคำสั่งที่ค้างเข้าตลาดที่ราคาเปิด
MarketClose  → mark-to-market ที่ราคาปิด
Rebalance    → คำนวณสัญญาณจากราคาปิด → วางคำสั่งไว้ให้เปิดวันถัดไป
```

ลำดับนี้สำคัญ: สัญญาณคำนวณจากราคาปิดวันนี้ แต่ **ซื้อขายที่ราคาเปิดวันถัดไป** ไม่ใช่ราคาปิดวันเดียวกัน

องค์ประกอบ:
- **Order state machine** — `PENDING → SUBMITTED → PARTIALLY_FILLED → FILLED / CANCELED`
- **Volume participation** — จำกัดไม่ให้ซื้อเกินสัดส่วนของ ADV จึงเกิด partial fill ได้
- **Double-entry accounting** — เงินสดและหุ้นต้องสมดุลเสมอ ไม่มี drift
- **ราคาหาย** — ถ้าวันไหนไม่มี bar ของหุ้นที่ถืออยู่ จะใช้ราคาปิดล่าสุดที่เคยเห็น ไม่ใช่ราคาทุน

### 4.4 Walk-forward ML

หน่วยสังเกตคือ **cross-section รายเดือน** ไม่ใช่รายวัน

- **Feature** = คะแนน factor ณ วันสิ้นเดือนนั้น
- **Label** = อันดับ (rank) ของผลตอบแทนเดือนถัดไปใน cross-section แปลงเป็นช่วง `[-0.5, 0.5]`
- ใช้ rank เพราะโจทย์คือ "เรียงลำดับหุ้น" ไม่ใช่ "ทำนายตัวเลขผลตอบแทน" และ rank ทนต่อ outlier

**Purge และ embargo:** label ของเดือนสุดท้ายในชุดเทรนจะไปคาบเกี่ยวกับชุดทดสอบ จึงตัดออก 1 งวด
แล้วเว้นอีก 1 งวดเพื่อตัด serial correlation ที่ยังเหลือ

**โมเดล 3 ตัว:**
| ชื่อ | คืออะไร |
|---|---|
| `composite` | ถ่วงน้ำหนักเท่ากันบน feature ที่ z-score แล้ว — เป็น baseline |
| `ridge` | linear ranker แบบ L2 แก้สมการด้วย Gaussian elimination เขียนเอง |
| `gbdt` | gradient boosted trees เขียนเอง **ไม่ใช่ LightGBM หรือ scikit-learn** |

**กติกาเลือกผู้ชนะ:** โมเดลต้องชนะ baseline เกิน 0.005 rank IC ถึงจะได้ที่นั่ง
ถ้าไม่ถึง baseline อยู่ต่อ — เพราะถ้าเทียบด้วยคะแนนดิบเฉย ๆ ผู้ชนะคือโมเดลที่ดวงดีบน test fold

### 4.5 Falsification layer

ทำงานเป็นลำดับขั้น หยุดทันทีถ้าด่านแรกไม่ผ่าน

**ขั้นที่ 1 — Hard gates (ห้ามข้าม)**
`authority`, `lookahead_leakage`, `data_integrity`, `reproducibility`
ถ้าเจอ temporal leakage ผลลัพธ์คือ `REJECTED` ทันที ไม่มีสถิติไหนมาแก้ต่างได้

**ขั้นที่ 2 — Robustness (รันกลยุทธ์ใหม่จริงทุกจุด)**
- Parameter sweep: รันที่ top 20 / 30 / 50 แล้วดูว่าเป็น plateau หรือ spike
- Factor ablation: ถอด factor ทีละตัวแล้วรันใหม่ ดูว่าตัวไหนมีส่วนช่วยจริง
- Cost stress: กวาดค่าธรรมเนียมจนหา break-even
- Concentration: Herfindahl index ดูว่ากระจุกตัวไหม
- Subperiod: ผลตอบแทนแยกรายปี

**ขั้นที่ 3 — สถิติ**
- Stationary block bootstrap (Politis & Romano) หา confidence interval ของ Sharpe
- Deflated Sharpe Ratio (Bailey & López de Prado) หักผลของจำนวน trial + skew + kurtosis

**ผลตัดสิน 4 ระดับ:** `REJECTED` → `RESEARCH_ONLY` → `VALIDATED` → `PAPER_CANDIDATE`

### 4.6 Paper operations

จำลองการเดินระบบรายวัน: สร้างคำสั่ง → ส่งเข้า broker จำลอง → บันทึก fill ลง SQLite → กระทบยอดตอนปิดตลาด

**Recovery drill:** ทิ้ง account state ทั้งหมด เปิดฐานข้อมูลใหม่ อ่าน fill กลับมา แล้วสร้างยอดเงินสดและ position ขึ้นใหม่
สำคัญตรงที่ต้อง**อ่านกลับจาก disk** ไม่ใช่ replay object ที่ยังอยู่ใน memory เพราะอย่างหลังพิสูจน์แค่เลขคณิต ไม่ได้พิสูจน์ว่า ledger เขียนลงจริง

### 4.7 Interface

```
CLI สร้าง artifact (มี hash)  →  REST API เสิร์ฟ  →  dashboard / MCP อ่าน
```

**ไม่มี** endpoint ไหนสั่งรัน backtest ได้ เพราะ backtest 30 ปีใช้เวลาเป็นนาที และการให้ผลลัพธ์
ผูกกับ artifact ที่มี hash หมายความว่าทุกตัวเลขบนหน้าจอย้อนกลับไปหาไฟล์ต้นทางได้

ถ้า artifact ยังไม่ถูกสร้าง หน้าจอจะแสดง**คำสั่งที่ต้องรัน** ไม่ใช่กราฟเปล่าหรือเลขศูนย์

---

## 5. เทคนิคเชิงควอนต์ที่ใช้

### 5.1 การปรับ corporate action แบบย้อนหลัง

Split อัตราส่วน R → ราคาก่อนหน้าคูณ `1/R`, ปริมาณคูณ `R`
Dividend D ณ ex-date → ราคาก่อนหน้าคูณ `(1 - D/P)` โดย P คือราคาปิดวันก่อน ex-date

ทั้งสองคูณสะสมย้อนหลังจากบาร์ล่าสุดกลับไป

**กับดักที่เจอจริง:** ราคา `Close` ของ Yahoo ปรับ split มาแล้ว ถ้าเอาไปใช้เป็นราคาดิบพร้อมกับบันทึก split ด้วย
split จะถูกใช้สองรอบ ราคาก่อน split 4:1 จะเหลือ 1/4 ของค่าจริง และเงินปันผลก็ประกาศในหน่วยหลัง split เหมือนกัน

### 5.2 Information Coefficient และ t-statistic

- **Pearson IC** = correlation ระหว่างคะแนน factor กับผลตอบแทนล่วงหน้าใน cross-section
- **Rank IC (Spearman)** = แบบเดียวกันแต่ใช้ลำดับ ทนต่อ outlier มากกว่า
- **IR** = `mean(IC) / sd(IC)` ต่อ 1 งวด rebalance
- **t-statistic** = `IR × sqrt(N)`

**Newey-West:** ช่วงผลตอบแทนล่วงหน้าคาบเกี่ยวกัน ทำให้ IC ติดกันมี serial correlation
t-stat แบบธรรมดาจึงเกินจริง ต้องขยาย standard error ด้วย autocovariance (Bartlett kernel, 3 lags)

### 5.3 Deflated Sharpe Ratio

$$\text{DSR} = \Phi\left(\frac{SR - E[\max_N]}{\sigma_{SR}}\right), \quad
\sigma_{SR} = \sqrt{\frac{1 - S \cdot SR + \frac{K-1}{4}SR^2}{T-1}}$$

โดย $E[\max_N]$ คือ Sharpe สูงสุดที่คาดว่าจะได้จากการลอง N ครั้งภายใต้สมมติฐานว่าไม่มี edge เลย

**สองจุดที่ต้องระวัง:**
1. $SR$ ต้องเป็น Sharpe **ต่อคาบ** และ $T$ ต้องนับในหน่วยเดียวกัน ถ้าใส่ Sharpe รายปีคู่กับ T รายวัน ค่าจะพองขึ้นราว $\sqrt{252}$ เท่า
2. $S$ (skewness) กับ $K$ (kurtosis) ต้อง**ประมาณจากข้อมูลจริง** ไม่ใช่สมมติว่าปกติ เพราะเหตุผลทั้งหมดของสถิติตัวนี้คือแก้ผลของหางอ้วน

### 5.4 Stationary block bootstrap

สุ่มเป็นบล็อกที่ความยาวสุ่มแบบ geometric (คาดหวัง 21 วัน) แทนที่จะสุ่มทีละวัน
เพราะการสุ่มทีละวันทำลาย autocorrelation ของผลตอบแทน ทำให้ confidence interval แคบเกินจริง

### 5.5 Label-shuffle permutation test

สลับ label ภายในแต่ละ cross-section โดยไม่แตะ feature, fold, purge หรือการกระจายตัวของ label
ถ้าโมเดลยังทำคะแนนได้ แปลว่าระบบวัดอย่างอื่นอยู่ ไม่ใช่ความสามารถในการทำนาย

**สลับครั้งเดียวพิสูจน์ไม่ได้** — โมเดล fit ใหม่ทุก fold ดังนั้น effective sample size ใกล้เคียงจำนวน fold (24)
มากกว่าจำนวน cross-section ทดสอบ (~288) การที่ครั้งหนึ่งบังเอิญได้คะแนนสูงกว่าของจริงเป็นเรื่องปกติ
จึงต้องสลับหลายครั้งแล้วรายงาน empirical p-value พร้อม add-one smoothing (`(k+1)/(n+1)`)

### 5.6 Red team

3 กรณีที่จงใจสร้างมาให้ระบบปฏิเสธ

| กรณี | สร้างอะไร | ต้องได้ผลว่า |
|---|---|---|
| Lookahead | กลยุทธ์ที่แอบดูอนาคต ผลตอบแทนสวยเกินจริง | `REJECTED` แม้ตัวเลขจะสวย |
| Random mining | ลองกลยุทธ์สุ่ม 100 อัน แล้วเอาอันที่ดีที่สุดมาเสนอ | เตือน multiple testing |
| Cost illusion | edge 3% ต่อปี แต่หมุนพอร์ต 25 รอบต่อปี | edge หายเมื่อคิดต้นทุน |

---

## 6. การทดสอบ

รวม **286 tests** (ผ่านทั้งหมด, skip 2) ตัวเลขด้านล่างนับจากจำนวนฟังก์ชัน `def test_`
ซึ่งน้อยกว่าที่ pytest รายงานเล็กน้อย เพราะ `parametrize` ทำให้ฟังก์ชันเดียวรันหลายเคส

| กลุ่ม | จำนวน | ทดสอบอะไร |
|---|---|---|
| `tests/factors/` | 28 | สูตร factor, ไม่ใช้ข้อมูลอนาคต, split/dividend, missingness, การจัดอันดับเมื่อค่าเท่ากัน |
| `tests/backtest/` | 26 | บัญชี, order state, ต้นทุน, delisting, golden regression, determinism |
| `tests/validation/` | 24 | gate, bootstrap, DSR, sensitivity, trial ledger, verdict |
| `tests/data/` | 23 | PIT facade, corporate action, dataset isolation, market bar |
| `tests/e2e/` | 18 | CLI ทุกคำสั่งแบบ end-to-end |
| `tests/portfolio/` | 14 | คัดเลือก, ถ่วงน้ำหนัก, constraint, สภาพคล่อง |
| `tests/ml/` | 13 | walk-forward split, purge/embargo, โมเดล, determinism |
| `tests/common/` `tests/infrastructure/` `tests/application/` | 27 | hashing, artifact, partition, service |
| `tests/mcp/` `tests/api/` | 15 | tool schema, JSON-RPC, REST endpoint |
| `tests/domain/` | 7 | contract, identity, value object |
| `tests/paper/` | 7 | broker, กระทบยอด, กู้คืน, trade break |
| `tests/architecture/` | 4 | dependency direction, ML boundary |
| `tests/red_team/` | 3 | 3 กรณีหักล้าง |
| root + อื่น ๆ | 65 | scope guard, milestone gate, release signature, agent, analytics, universe |

### เทสต์ที่สำคัญเป็นพิเศษ

ตารางนี้คือพฤติกรรมที่ถ้าพังแล้ว**ไม่มีอะไรฟ้อง** ตัวเลขจะยังดูปกติ

| ไฟล์ | ถ้าไม่มี จะพังยังไง |
|---|---|
| `test_golden_backtest.py` | ผล backtest เปลี่ยนไปเงียบ ๆ หรือรันสองครั้งได้คนละค่า |
| `test_pipeline_determinism.py` | ML panel สร้างไม่เหมือนเดิม ตรวจสอบ rank IC ที่รายงานไม่ได้ |
| `test_dataset_idempotency.py` | `dataset build` ซ้ำ ทำให้ corporate action ซ้ำ split 4:1 กลายเป็น 16 |
| `test_dataset_isolation.py` | dataset สองชุดที่มี ticker เดียวกันเขียนทับราคากันเอง |
| `test_stale_price_marking.py` | วันที่ไม่มีข้อมูลถูกตีราคาเป็นราคาทุน สร้าง return รายวันสองหลักที่ไม่เคยเกิด |
| `test_multiple_testing.py` | DSR ถูกป้อนหน่วยรายปี หรือสมมติว่าผลตอบแทนเป็น normal |
| `test_release_signature.py` | ลายเซ็นไม่ครอบคลุมบางฟิลด์ แก้ verdict หลังเซ็นได้ |

เจ็ดข้อแรกมาจากบั๊กที่เกิดขึ้นจริงระหว่างพัฒนา ทุกตัวให้ผลลัพธ์ที่ดูสมเหตุสมผลและไม่ raise error

### การทดสอบเป็น hermetic

- ไม่ใช้เครือข่าย (มี socket guard)
- ไม่พึ่งสถานะที่ค้างจากการรันครั้งก่อน — ทุกเทสต์ build ลง temp directory
- มี guard ใน `conftest.py` ที่ **fail ถ้าเทสต์เขียนทับ artifact ในเรพอ**

### Quality gate อื่น ๆ

```bash
ruff check . && ruff format --check .   # lint + format
mypy quantlab apps                       # strict type check, 166 ไฟล์
python scripts/check_scope.py M9         # กันงานที่เกินขอบเขต V1
python scripts/verify_market_data.py     # ตรวจ corporate action กับ provider
python scripts/restore_drill.py          # ซ้อมกู้คืนจาก fill ledger
python scripts/run_v1_acceptance.py      # รันทุกขั้นตอน end-to-end
python scripts/verify_release.py         # ตรวจว่า acceptance record ไม่ถูกแก้
```

---

## 7. ผลลัพธ์จริงและวิธีอ่าน

### ข้อมูล

101 หลักทรัพย์สหรัฐฯ ปี 1995–2024: **7,552 วันทำการ, 730,370 แท่งราคา, 10,855 corporate action**
แบ่งเป็นหุ้น 95 ตัวใน 11 sector และ ETF 6 ตัวที่กันไว้เป็น benchmark ไม่ปนใน cross-section

### ผลตรวจสอบข้อมูล

101/101 ตัวผ่าน median error 0.0000% worst single bar 0.478%

### Momentum 30 ปี

Rank IC `+0.0123`, t-stat `+0.98` (Newey-West) → **ไม่มีนัยสำคัญทางสถิติ**
quintile ไม่ monotonic — spread มาจาก bucket บนสุดเกือบทั้งหมด

**IC รายปีจับ momentum crash ที่เกิดขึ้นจริงได้เอง** โดยไม่ได้บอกมันก่อน:
2000 (−0.155), 2009 (−0.155), 2016 (−0.101) — เป็นสัญญาณว่าท่อข้อมูลถูกต้อง แม้สัญญาณจะอ่อน

### Backtest 2015–2024

CAGR `+21.83%` เทียบ SPY `+13.03%`, beta `1.10`, Jensen alpha `+6.74%`, Sharpe `1.04`, maxDD `−35.17%`

**ต้องอ่านคู่กับ survivorship bias** จักรวาลที่ทุกตัวรอดมาถึงปี 2024 วิ่งผ่านตลาดกระทิง 2015–2024 ควรจะดูดีอยู่แล้ว

### Falsification

**`RESEARCH_ONLY`** — Deflated Sharpe p = 0.0027 ต่ำกว่าเกณฑ์ 0.95 มาก

ทุกอย่างก่อนหน้าบรรทัดสุดท้ายดูดี: parameter surface เป็น plateau, ทุก factor มีส่วนช่วยเป็นบวก,
edge ทน 700 bps, bootstrap CI ไม่คร่อมศูนย์ แต่พอหักจำนวน trial (7 ครั้ง) และ excess kurtosis 11 แล้ว ไม่ผ่าน

**นี่คือระบบทำงานถูกต้อง** backtest ที่ให้ผล 617% เป็นส่วนที่ง่าย ส่วนที่มีค่าคือชั้นที่ไม่ยอมเรียกมันว่าการค้นพบ

---

## 8. Workflow การใช้งาน

### ครั้งแรก

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,data,api]"
quantlab doctor
pytest -q
```

### ทำงานกับข้อมูลจริง

```bash
# 1. ดาวน์โหลด (ไม่ commit ลง repo เพราะติด ToS ของ provider)
python scripts/download_real_market_data.py \
    --universe configs/universes/us-research-v1.yaml \
    --start 1995-01-01 --end 2025-01-01

# 2. ตรวจก่อนใช้ — ขั้นนี้ห้ามข้าม
python scripts/verify_market_data.py --fixture us_research

# 3. build dataset
quantlab dataset build configs/datasets/us-research-30y.yaml
```

### วงจรวิจัย

```bash
quantlab factor research momentum_12_1 --dataset DATASET-US-30Y-v001
quantlab backtest run configs/strategies/us-price-composite-v1.yaml \
    --dataset DATASET-US-30Y-v001 --start 2015-01-02 --end 2024-12-31
quantlab model compare --dataset DATASET-US-30Y-v001 --control --permutations 8
quantlab validate run configs/validation/default-v1.yaml \
    --strategy configs/strategies/us-price-composite-v1.yaml \
    --dataset DATASET-US-30Y-v001 --start 2015-01-02 --end 2024-12-31
```

### ดูผลบนหน้าเว็บ

```bash
python -m uvicorn apps.api.app:app --port 8000
cd apps/web && npm install && npm run dev
```

### เวลาที่ใช้จริง

| งาน | เวลา |
|---|---|
| `dataset build` 30 ปี | ~1.5 นาที |
| `factor research` 30 ปี | ~4 นาที |
| `backtest` 10 ปี | ~4 นาที |
| `validate` พร้อม sweep เต็ม | ~15 นาที |
| `model compare` + 8 permutation | ~35 นาที |

ช้าเพราะเป็น pure Python และใช้ `Decimal` กับราคา — เป็นราคาที่จ่ายเพื่อไม่ต้องพึ่ง scientific stack

---

## 9. ข้อจำกัดที่ต้องรู้

| ข้อจำกัด | ผลกระทบ |
|---|---|
| **Survivorship bias** | จักรวาลมีแต่ตัวที่ยังอยู่ ผลตอบแทนสูงเกินจริง แก้ไม่ได้ด้วยข้อมูลฟรี |
| **ไม่มี PIT fundamentals บนข้อมูลจริง** | ไม่มีแหล่งฟรีที่มี `available_at` เชื่อถือได้ งานวิจัยบนข้อมูลจริงจึงใช้ได้แค่ factor ฝั่งราคา |
| **ไม่มี liquidity universe** | spec กำหนดให้สร้าง universe แบบ PIT รายเดือน แต่ตอนนี้ใช้รายชื่อคงที่ที่เลือกมือ ซึ่งเป็นอีกช่องของ selection bias |
| **Long only, daily bar** | ไม่มี short ไม่มี leverage ตัวเลข long/short เป็นแค่ diagnostic |
| **ต้นทุนเป็นแบบจำลอง** | cost sweep บอกว่า edge ทนแรงเสียดทานได้แค่ไหน ไม่ได้บอกว่าถ้าส่งคำสั่งจริงจะเสียเท่าไร |
| **ไม่มี forward track record** | paper layer ทำงานได้ แต่ยังไม่มีการรันไปข้างหน้านานพอจะนับเป็นหลักฐาน out-of-sample |
| **ช้า** | ดูตารางเวลาข้างบน |

---

## 10. แนวทางต่อยอด

### ระดับ 1 — เพิ่มความน่าเชื่อถือของหลักฐาน (ผลตอบแทนสูงสุดต่อแรงที่ลง)

1. **แก้ survivorship bias** — หาแหล่งข้อมูลที่มีหุ้นถูกถอดถอน (CRSP, Sharadar, Norgate)
   โครงสร้างรองรับอยู่แล้ว: `listings.csv` มีคอลัมน์ `delisted_date` และ synthetic fixture ทดสอบเส้นทางนี้ไว้แล้ว
   นี่คือข้อจำกัดที่กระทบผลลัพธ์มากที่สุด

2. **สร้าง liquidity universe แบบ PIT** — ตาม spec §2.6: ทุกสิ้นเดือนคัดจากราคา ≥ $5,
   มีประวัติ ≥ 252 วัน, เรียงตาม median dollar volume 60 วัน แล้วเอา top N
   จะได้ตัด selection bias จากการเลือกรายชื่อด้วยมือ

3. **เพิ่ม PIT fundamentals จาก SEC EDGAR** — ดึง filing date จริงเพื่อให้ factor ฝั่ง value/quality/growth
   ใช้ได้กับข้อมูลจริง โครงสร้าง dual-timestamp (`period_end` vs `available_at`) มีอยู่แล้ว

4. **รัน paper trading ไปข้างหน้าจริง** — ต่อกับ Alpaca paper API แล้วเดินระบบทุกวัน
   สะสม forward evidence ให้พอที่จะเลื่อนจาก `RESEARCH_ONLY` ขึ้นได้

### ระดับ 2 — ขยายความสามารถ

5. **Sector neutralization** — ตอนนี้มี sector metadata แล้วแต่ยังไม่ได้ใช้ neutralize
   ควรเพิ่มการจัดอันดับภายใน sector และ regression-style neutralization

6. **เพิ่ม factor** — spec วางไว้ราว 14 ตัวและทำครบแล้ว ขั้นถัดไปคือ
   quality ที่ละเอียดขึ้น, factor ที่อิงตัวแปรมหภาค, หรือ residual momentum

7. **CPCV (Combinatorial Purged Cross-Validation) และ PBO** — spec §7.10 ระบุว่าเป็น stretch goal
   ตอนนี้มี walk-forward แบบ purged แล้ว ต่อยอดเป็น CPCV เพื่อคำนวณ Probability of Backtest Overfit ได้

8. **Weighting เพิ่มเติม** — ตอนนี้ equal weight ควรเพิ่ม inverse-volatility, risk parity
   แล้วให้ validation sweep เปรียบเทียบ

### ระดับ 3 — วิศวกรรม

9. **เร่งความเร็ว** — คอขวดคือการสร้าง `MarketBar` (Decimal) นับล้านครั้ง
   ทางเลือก: เพิ่ม read path แบบเบาสำหรับงานที่ต้องการแค่ราคาปิด, cache ผลปรับราคาต่อ (instrument, as_of),
   หรือย้ายเฉพาะ hot path ไป numpy โดยยังคง Decimal ในเส้นทางบัญชี

10. **Parquet จริง** — ตอนนี้ partition เป็น JSON ซึ่งชัดเจนและตรวจสอบง่าย
    ถ้าข้อมูลโตขึ้นมาก การย้ายไป Parquet + DuckDB จะคุ้ม (แต่ต้องยอมรับ dependency)

11. **CI ที่รันข้อมูลจริง** — ตอนนี้ CI รันแค่ synthetic fixture
    เพิ่ม job รายสัปดาห์ที่ดาวน์โหลดข้อมูล ตรวจ corporate action แล้วเทียบ manifest hash

12. **Dashboard เชิงโต้ตอบ** — ตอนนี้อ่าน artifact อย่างเดียว
    อาจเพิ่มหน้าเทียบหลาย run, ดู decision trace ของแต่ละ rebalance, หรือ drill-down รายหุ้น

### ระดับ 4 — สิ่งที่ **ไม่ควร** ทำ

spec ระบุ non-goal ไว้ชัดในหัวข้อ Executive Summary และมี `scripts/check_scope.py` บังคับ:
เงินจริง, intraday/tick/HFT, options, futures, FX, crypto, short, leverage,
reinforcement learning, LSTM/Transformer สำหรับทำนายราคา, alternative data, factor library 100+ ตัว

เหตุผลไม่ใช่ว่าสิ่งเหล่านี้ไม่ดี แต่เพราะแต่ละอย่างเพิ่มพื้นที่ให้ overfit
ก่อนที่ระบบจะพิสูจน์ได้ว่าจับ edge ธรรมดา ๆ ได้จริงเสียก่อน

---

## 11. เอกสารอื่นในโปรเจค

| ไฟล์ | เนื้อหา |
|---|---|
| [README.md](../README.md) | ภาพรวมพร้อมผลลัพธ์และรูป |
| [docs/architecture/market-data-v1.md](architecture/market-data-v1.md) | ท่อข้อมูล การปรับ corporate action และข้อจำกัด |
| [docs/architecture/dependency-rules.md](architecture/dependency-rules.md) | กฎ dependency ระหว่างชั้น |
| [docs/architecture/paper-operations-v1.md](architecture/paper-operations-v1.md) | วงจรการเดินระบบรายวัน |
| [docs/calculators/factors-v1.md](calculators/factors-v1.md) | นิยามคณิตศาสตร์ของ factor ทั้ง 14 ตัว |
| [docs/calculators/statistics-v1.md](calculators/statistics-v1.md) | bootstrap, DSR, Newey-West, FDR |
| [docs/calculators/ml-v1.md](calculators/ml-v1.md) | panel, walk-forward, โมเดล, permutation test |
| [docs/calculators/performance-v1.md](calculators/performance-v1.md) | สูตร metric และ benchmark-relative |
| [docs/superpowers/specs/](superpowers/specs/) | spec ออกแบบฉบับเต็ม พร้อมหมายเหตุว่าอะไรสร้างต่างจากที่ออกแบบ |
