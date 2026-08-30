# استراتيجية محرك القرار — الحالة الفعلية بالكود (بعد إصلاحات 14-18/8)

مرجع تقني كامل للاستراتيجية **كما هي منفَّذة اليوم فعلياً** بـ `ict_engine.py`
و`ai_engine_v5.py` — كل ادّعاء هون مربوط برقم سطر حقيقي بالكود، مو بتعليقات
قديمة ممكن تكون عفا عليها الزمن. لاحظت أثناء إعداد هالملف إنه `SIGNALS_AND_ANALYSIS.md`
الموجود يوصف "rescue layers" وكأنها لسا نشطة بمسار القرار — هاد **غير صحيح
اليوم** (معطّلة بالكامل من 14/8، تفصيل بالقسم 3.5)، وهو بالضبط نوع الانحراف
يلي هالملف مبني ليتجنبه.

---

## 1. الأساس النظري — ICT/SMC + إضافات كلاسيكية محدودة

كل هاي المفاهيم محسوبة من شموع OHLC خام (`smart_data.py::_add_indicators`,
سطر 452-489، يضيف `atr/rsi/ema_20/50/200/macd/macd_signal/macd_hist/bb_*`
لكل DataFrame قبل ما يوصل لـ ict_engine).

| المفهوم | أين بالكود | الشرط الرياضي بالضبط |
|---|---|---|
| **Swing High/Low** | `find_swing_points()`, [ict_engine.py:36-72](backend/app/services/ict_engine.py#L36-L72) | شمعة `i` أعلى/أقل من `strength` شمعة على كل جانب (strength=3 أو 5 حسب المستدعي) |
| **Order Blocks** | `detect_order_blocks()`, [L76-176](backend/app/services/ict_engine.py#L76-L176) | آخر شمعة هابطة (`close<open`) تلاها ≥2 شمعات صاعدة بحركة >0.3×ATR لكل وحدة = Bullish OB (والعكس للـBearish). يُستبعد لو `mitigated` (السعر تجاوزه) أو بعيد >5% |
| **Fair Value Gap (FVG)** | `detect_fvg()`, [L180-257](backend/app/services/ict_engine.py#L180-L257) | فجوة صاعدة: `low[i] > high[i-2]`. هابطة: `high[i] < low[i-2]`. يُستبعد لو "ممتلئة" (السعر دخلها) أو بعيد >8% |
| **BOS / CHoCH** | `analyze_market_structure()`, [L261-359](backend/app/services/ict_engine.py#L261-L359) | ترند = HH+HL→BULLISH، LH+LL→BEARISH، غير ذلك RANGING. BOS = السعر الحالي تجاوز آخر Swing High/Low غير مكسور. CHoCH = أول BOS بعكس الترند السائد |
| **Liquidity Pools (BSL/SSL)** | `detect_liquidity_pools()`, [L363-435](backend/app/services/ict_engine.py#L363-L435) | Equal Highs/Lows بفارق ≤0.2% بين قمتين/قاعين → مستوى سيولة. `swept` = السعر تجاوزه فعلاً |
| **Liquidity Sweep / Stop Hunt** | `detect_liquidity_sweeps()`, [L439-570](backend/app/services/ict_engine.py#L439-L570) | شمعة اخترقت مستوى سيولة (`high>level`) ثم أغلقت تحته بشوكة >0.25×ATR وجسم >0.05×ATR وباتجاه معاكس = "رفض مؤكد". الجودة: STRONG (خلال ≤5 شموع + شوكة ≥0.5×ATR) / MODERATE / WEAK (اكتساح بلا رفض) / NONE |
| **Premium/Discount Zone** | `analyze_premium_discount()`, [L574-637](backend/app/services/ict_engine.py#L574-L637) | نسبة موقع السعر ضمن مدى آخر 50 شمعة (Fibonacci 50%). ≥75%=EXTREME_PREMIUM(SELL)، ≥55%=PREMIUM، 45-55%=EQUILIBRIUM، ≥25%=DISCOUNT، أقل=EXTREME_DISCOUNT(BUY) |
| **Kill Zones** | `get_kill_zone()`, [L641-707](backend/app/services/ict_engine.py#L641-L707) | نوافذ UTC ثابتة: Asia 00-04، London Open 07-09 (الأقوى)، London Close 11-13، NY Open 13:30-15:30 (الأقوى)، Midnight 23-01 |
| **Wyckoff Phases** | `analyze_wyckoff()`, [L711-783](backend/app/services/ict_engine.py#L711-L783) | مقارنة EMA20/50 + اتجاه السعر 5/20 شمعة + الفوليوم مقابل متوسطه → MARKUP/MARKDOWN/ACCUMULATION/DISTRIBUTION/RANGING |

**مؤشرات كلاسيكية إضافية: RSI(14) وMACD(12,26,9)** — محسوبة دايماً (مو
اختيارية)، وتُستخدم **فقط كعاملين إضافيين صغيرين** ضمن نظام النقاط
(5 نقاط لكل واحد من أصل 100) — راجع القسم 2. لا يوجد EMA crossover ولا
Bollinger Bands ضمن القرار رغم إنهم محسوبين ومُرجَعين بالـ`indicators`
للعرض فقط ([L1279-1287](backend/app/services/ict_engine.py#L1279-L1287)).

---

## 2. نظام النقاط (Confluence Scoring) — `calculate_confluence()`

[ict_engine.py:787-983](backend/app/services/ict_engine.py#L787-L983) — **حي ومستخدَم فعلياً**، مو كود ميت: نتيجته
(`bull_score`/`bear_score`) هي المُدخل الخام يلي `_decision_finalizer` بمحرك
القرار يبني عليه `score_delta` (تفصيل بالقسم 3). الحد الأقصى النظري 100 نقطة
(`min(score, 100)`).

| المعيار | النقاط | الشرط الدقيق |
|---|---|---|
| Market Structure | 20 | `trend == BULLISH/BEARISH` |
| Order Block | 25 | السعر داخل OB صاعد/هابط فعلياً (`in_bullish_ob`/`in_bearish_ob`) |
| Fair Value Gap | 15 (أو 8) | السعر داخل FVG = 15. قريب منه (<0.5%) بدون دخول = 8 |
| Premium/Discount Zone | 15 (أو 10) | EXTREME = 15، عادي = 10 |
| Liquidity Sweep + رفض | 25 / 15 / 5 | STRONG=25، MODERATE=15، اكتساح بلا رفض=5 |
| Kill Zone | 10 (أو 5) | وقت مثالي (London/NY Open)=10، أي Kill Zone تاني=5 |
| Wyckoff | 10 (أو 6) | إشارة فعلية (BUY/SELL_SIGNAL)=10، تحضيرية (PREPARE)=6 |
| RSI | 5 | <30 (ذعر بيعي→bull) أو >70 (ذعر شرائي→bear) |
| MACD | 5 | تقاطع histogram من سالب لموجب (أو العكس) بين آخر شمعتين |
| **عقوبة**: `sweep_quality == NONE` | −8 | من الاتجاهين معاً ([L896-898](backend/app/services/ict_engine.py#L896-L898)) |

**التماثل بين BUY/SELL: مؤكَّد صراحة بقراءة الكود** — كل شرط أعلاه مكرر
بصيغة مطابقة لـ`bull_score`/`bear_score` بنفس القيم بالضبط (فحصت كل سطر،
[L811-946](backend/app/services/ict_engine.py#L811-L946)). لا يوجد أي انحياز مبرمج لاتجاه على حساب التاني.

⚠️ **مهم**: `calculate_confluence()` نفسها بترجّع كمان `direction` (BUY/SELL/WAIT
لو `confidence≥40`) و`quality` (PREMIUM/STANDARD/LOW) — **هذول الاثنين لا
يُستخدَمان مباشرة بالقرار النهائي**. محرك `ai_engine_v5.py` بيتجاهلهم ويعيد
حساب الاتجاه والجودة لحاله بمنطق منفصل تماماً (القسم 3) — بس **نقاط
bull_score/bear_score نفسها** هي يلي بتنتقل فعلياً.

---

## 3. مسار القرار الكامل — بالترتيب الحقيقي وأرقام الأسطر

من [ai_engine_v5.py::analyze_market()](backend/app/services/ai_engine_v5.py#L144)، الاستدعاءات بالترتيب الفعلي:

```
بيانات خام (smart_data.get_ohlcv) — LTF + HTF بالتوازي           [L205-208]
        │
ict_engine.full_analysis(df_ltf)  → ltf_analysis                  [L222]
ict_engine.full_analysis(df_htf)  → htf_analysis (لو متوفر)       [L226]
        │  (بينهم: Gemini لتحسين النص العربي فقط — بدون اتجاه ولا مستويات [L234-258])
_auto_calibrate_thresholds()      → يضبط delta/RR/tolerance       [L291]
        │
_decision_finalizer()             → BUY/SELL/WATCHLIST            [L294]
        │  (لو رجّعت BUY/SELL فقط:)
_institutional_gate()             → رفض صارم Rules 1-16           [L298]
        │  (لو institutional_gate_passed:)
_output_safety_gate()             → طبقة أمان 7 قواعد نهائية      [L301]
        │  (لو لسا BUY/SELL:)
_confidence_calibration_layer()   → % الثقة النهائي                [L304]
_classify_trade_mode()            → SWING / SCALP                  [L308]
        │
_explainability_layer()           → أثر تدقيق (يعمل دايماً، آخر خطوة) [L341]
_normalize_output_layer()         → توحيد شكل المخرجات              [L344]
```

**rescue layers (`_smart_rescue_layer`, `_borderline_rescue_layer`,
`_smart_rr_recovery`) معطّلة بالكامل من مسار الإنتاج منذ 14/8** — الاستدعاءات
موجودة بس **معلَّقة بالكومنت** ([L319-332](backend/app/services/ai_engine_v5.py#L319-L332))، والدالة الثالثة
(`_smart_rr_recovery`) **صفر استدعاء بالكود كله حتى بالكومنتات** — موجودة
كدوال فقط لأي تحليل/محاكاة أوفلاين مستقبلي، لا تأثير على أي قرار حي.

### 3.1 `_decision_finalizer` — [L1727-2089](backend/app/services/ai_engine_v5.py#L1727-L2089) (بناء الاتجاه والثقة الخام)

1. **بناء `score_delta`**: `bull_score - bear_score` من قسم 2 ([L1753-1755](backend/app/services/ai_engine_v5.py#L1753-L1755))
2. **عقوبات جودة (سكور فقط، لا رفض)**:
   - ضجيج فريم منخفض (1m/5m/15m بلا sweep+structure قوي): −15 ([L1760-1773](backend/app/services/ai_engine_v5.py#L1760-L1773))
   - فخ Range (OBs متداخلة بلا BOS): −20 ([L1775-1780](backend/app/services/ai_engine_v5.py#L1775-L1780))
3. **تعديل الـsweep**: STRONG +3.5، MODERATE +1.5، WEAK −1.2، معدوم −3.0 ([L1816-1824](backend/app/services/ai_engine_v5.py#L1816-L1824))
4. **buffer حسب حالة السوق**: RANGING +2.5، VOLATILE +2.0، TRENDING +1.5 ([L1828-1835](backend/app/services/ai_engine_v5.py#L1828-L1835))
5. **`effective_delta`** = `|score_delta| + sweep_adj + buffer − noise_penalty − trap_penalty` ([L1836-1842](backend/app/services/ai_engine_v5.py#L1836-L1842))
6. لو `effective_delta < threshold` (من المعايرة التلقائية، قسم 4) → **WATCHLIST** (مو رفض، حالة انتظار) ([L1863-1872](backend/app/services/ai_engine_v5.py#L1863-L1872))
7. **حل تعارض الاتجاه**: `score_delta` هو المرجع الأساسي (`resolved = score_dir`)، والبنية (BOS/CHoCH) بس تحذّر لو خالفته بسوق RANGING، ما تغيّر القرار ([L1926-1943](backend/app/services/ai_engine_v5.py#L1926-L1943))

### 3.2 القواعد المطلقة (Veto — بدون استثناء) مقابل القواعد الوزنية

| النوع | القاعدة | الموقع | الاستثناءات |
|---|---|---|---|
| 🔴 **Veto مطلق** | تعارض HTF | [L1944-1966](backend/app/services/ai_engine_v5.py#L1944-L1966) | **لا يوجد** — أُلغي استثناء delta العالي بتاريخ 14/8 صراحة (موثّق بالكومنت) |
| 🔴 **Veto مطلق** | تعارض Zone (BUY بمنطقة Premium / SELL بمنطقة Discount) | [L1972-1983](backend/app/services/ai_engine_v5.py#L1972-L1983) | لا يوجد |
| 🔴 **Veto مطلق** | RR أقل من الحد الأدنى المعايَر | [L2306-2312](backend/app/services/ai_engine_v5.py#L2306-L2312) | لا يوجد — `_smart_rr_recovery` معطّلة |
| 🔴 **Veto مطلق** | SL/TP بالاتجاه الغلط، أو RR نهائي <1.0 (تحقق مزدوج) | [L2273-2293](backend/app/services/ai_engine_v5.py#L2273-L2293) + [L2569-2586](backend/app/services/ai_engine_v5.py#L2569-L2586) | لا يوجد |
| 🔴 **Veto مطلق** | Confluence أقل من 2 من 3 عوامل (sweep/structure/OB) | [L2019-2049](backend/app/services/ai_engine_v5.py#L2019-L2049) | لا يوجد — HTF مستثنى عمداً من هالعد (فحص منفصل أصلاً) |
| 🔴 **Veto مطلق (XAUUSD فقط)** | Rule 6: يتطلب HTF aligned + zone صالحة + RR≥1.3 | [L2544-2567](backend/app/services/ai_engine_v5.py#L2544-L2567) | كان فيه استثناء 15m/30m، **أُلغي 18/8**، موحّد الآن على كل الفريمات |
| 🔴 **Veto مطلق** | ثقة نهائية <55% | Rule 5 بـ`_output_safety_gate`، ضمن [L2407-2593](backend/app/services/ai_engine_v5.py#L2407-L2593) | لا يوجد |
| 🟡 **وزني/عقوبة سكور** | غياب sweep، غياب structure، ضعف RR، ضيق SL/TP، بعد entry عن zone... | كل ما هو `*_warning` بـ`_institutional_gate`، [L2182-2270](backend/app/services/ai_engine_v5.py#L2182-L2270) | تُخصم من الثقة بـ`_confidence_calibration_layer`، لا ترفض |
| 🟡 **وزني** | تعارض HTF (Rule 14 بـ`_institutional_gate`، [L2365-2379](backend/app/services/ai_engine_v5.py#L2365-L2379)) وRule 1 بـ`_output_safety_gate` | **ملاحظة**: هالقاعدتين فعلياً **لا يمكن أن تُفعّلا أبداً** — أي تعارض HTF حقيقي يوصل لـ`_hard_reject` مباشرة بـ`_decision_finalizer` (القاعدة الحمراء أعلاه) قبل ما التنفيذ يوصل لهون أصلاً. موجودة كطبقة أمان احتياطية فقط، مو منطق فعّال اليوم |

**منع تكديس الصفقات** (`_has_active_signal`) و**قاطع سلسلة الخسائر**
(`_check_loss_streak_breaker`) **مو جزء من هالاستراتيجية إطلاقاً** — دول
إدارة مخاطر تقنية بـ`bot.py`، خارج `ai_engine_v5.py` بالكامل، تفصيل بالقسم 7.

---

## 4. الفروقات بين الفريمات

### 4.1 مرجع HTF

من [analyze_market() سطر 203](backend/app/services/ai_engine_v5.py#L203):
```python
htf_timeframe = "4h" if timeframe in ("1h", "15m", "30m") else "1d"
```
يعني **15m وnw1h وnw30m الثلاثة يشتركون بنفس المرجع (4h)**، بينما **4h نفسها
مرجعها 1d**. الأثر العملي: أي إشارة BUY/SELL على 15m أو 1h لازم تتفق مع
اتجاه شمعة 4h (وإلا Veto مطلق، قسم 3.2) — يعني 15m و1h **مو مستقلين
فعلياً عن بعض بمعنى "اتجاه أعلى"**، كلاهما محكومين بنفس سقف الـ4h. الاستقلالية
الحقيقية الوحيدة المضمونة هي بمنع التكديس (قسم 7) يلي بالفعل يعامل كل فريم
كمفتاح منفصل تماماً — مو بمنطق الاتجاه نفسه.

### 4.2 فروقات معايير القرار الفعلية بين الفريمات

من `_auto_calibrate_thresholds` ([L829-1031](backend/app/services/ai_engine_v5.py#L829-L1031)):

| الفريم | delta الأساسي | مدى delta المسموح | RR أدنى | تفاوت الدخول | عقوبات إضافية |
|---|---|---|---|---|---|
| 1m/5m/15m | نفس صيغة النظام (12 افتراضي حسب regime) | RANGING(10-18)/TRENDING(12-20)/VOLATILE(14-22) — **نفس المدى لكل الفريمات** | نفس صيغة النظام حسب الحالة | 0.25%-0.50% حسب التذبذب | **−10 على الثقة النهائية دايماً** ([L2703-2705](backend/app/services/ai_engine_v5.py#L2703-L2705))، وسقف ثقة أقصى 65% ([L2765-2766](backend/app/services/ai_engine_v5.py#L2765-L2766)) |
| 30m/1h/4h/1d | نفس الصيغة | نفس المدى | نفس الصيغة | نفس المنطق | لا عقوبة فريم إضافية |

**الخلاصة**: delta وRR وConfluence **موحّدين رياضياً بنفس المعادلة لكل الفريمات**
(لا يوجد جدول منفصل لكل فريم) — الفرق الوحيد الحقيقي بين الفريمات هو:
(أ) عقوبة ثقة -10 وسقف 65% حصراً للفريمات ≤15m، و(ب) اختلاف مرجع الـHTF
(4.1 فوق)، و(ج) فترة الصلاحية (تحت).

### 4.3 فترة الصلاحية (`expires_at`)

محسوبة بـ`bot.py` (نقطتي الحفظ `bot_analyze` [L203-205](backend/app/api/bot.py#L203-L205) و`bot_save_alert_signal`
[L832-833](backend/app/api/bot.py#L832-L833)، وأيضاً `signals.py` [L175-177](backend/app/api/signals.py#L175-L177)) — **مو جزء من محرك القرار**:

```python
tf_hours = {"1m":2, "5m":4, "15m":8, "30m":12, "1h":24, "4h":72, "1d":168}
expires_at = created_at + tf_hours.get(timeframe, 24) ساعة
```

---

## 5. إدارة المخاطر والمستويات

### 5.1 Entry

من `calculate_levels()` ([ict_engine.py:987-1041](backend/app/services/ict_engine.py#L987-L1041)):
- الافتراضي = السعر الحالي (`current`)
- لو فيه Order Block معاكس صالح **وقريب (<0.3% من السعر)**، الدخول يُسحَب لمنتصف الـOB (`ob["mid"]`) بدل السعر الحالي — [L1006-1008](backend/app/services/ict_engine.py#L1006-L1008) (BUY) و[L1025-1027](backend/app/services/ict_engine.py#L1025-L1027) (SELL)

### 5.2 Stop Loss

**مؤكَّد من تحليل XAGUSD السابق**: SL = أقرب Swing Low/High **+ 0.5×ATR** buffer
(مو مضاعف ATR ثابت من الدخول):
```python
# BUY:  sl = max(valid_lows_below_entry) - atr*0.5   [L1011-1013]
# SELL: sl = min(valid_highs_above_entry) + atr*0.5  [L1030-1032]
# Fallback (لا يوجد swing صالح إطلاقاً): entry ± atr*2   [L1015, L1034]
```
معناها: مسافة SL **محكومة ببنية السعر الحقيقية أولاً، ATR بس هامش أمان إضافي
صغير فوقها** — مو نسبة ثابتة من ATR. هذا يفسّر ليش `sl_distance/ATR` بيتفاوت
كتير بين صفقة وصفقة (تفصيل بتقرير XAGUSD المنفصل).

### 5.3 Take Profit (TP1/TP2/TP3)

مرحلتين مختلفتين:
1. **حساب أولي** بـ`calculate_levels()`: TP1=`entry±1.5×ATR`، TP2=`nearest_bsl/ssl`
   لو أبعد من entry بالاتجاه الصحيح وإلا `entry±3×ATR`، TP3=`entry±5×ATR`
   ([L1017-1021](backend/app/services/ict_engine.py#L1017-L1021), [L1036-1040](backend/app/services/ict_engine.py#L1036-L1040))
2. **إعادة حساب لاحقة بـ`_institutional_gate` Rule 10** ([L2329-2357](backend/app/services/ai_engine_v5.py#L2329-L2357)):
   لو فيه مستوى سيولة (BSL/SSL) أقرب وصالح (>0.3% عن الدخول)، **يُستبدَل** TP1/TP2/TP3
   بمواقع مبنية عليه: TP1 = قبل السيولة بـ0.3×ATR (تفادي الدخول بمنطقة السيولة
   مباشرة)، TP2 = عند السيولة بالضبط، TP3 = بعدها بـ1.5×ATR (استمرارية).

### 5.4 Risk/Reward — الحد الأدنى الفعلي اليوم

من `_auto_calibrate_thresholds` ([L898-913](backend/app/services/ai_engine_v5.py#L898-L913)):
- الأساس: **1.0 لسوق RANGING، 1.1 لغيره** (TRENDING/VOLATILE)
- لو winrate الإجمالي ≥68% (`_WINRATE_THRESHOLD`): **1.0 دايماً** بغض النظر عن الحالة (منع overfitting)
- لو winrate <40%: عقوبة إضافية، `min_rr = max(base+0.2, 1.3)`
- يُحدَّد نهائياً بحدود صلبة `_CALIB_RR_MIN`/`_CALIB_RR_MAX` (قسم clamp، [L985](backend/app/services/ai_engine_v5.py#L985))
- **استثناء XAUUSD الوحيد المتبقي**: RR≥1.3 صريح بغض النظر عن كل ما فوق (Rule 6، قسم 3.2)

---

## 6. الثقة (Confidence) — الصيغة الكاملة

من `_confidence_calibration_layer()` ([L2601-2802](backend/app/services/ai_engine_v5.py#L2601-L2802)) — **تستبدل الثقة الخام
بالكامل**، لا علاقة لها بـ`confluence["confidence"]` الأصلية من ict_engine:

```
raw = ict_score×0.40 + liquidity_quality×0.25 + structure_strength×0.20 + rr_score×0.15
```

| المكوّن | القيمة القصوى | الشرط |
|---|---|---|
| `ict_score` | = bull_score أو bear_score (من قسم 2)، سقف 100 | [L2643-2647](backend/app/services/ai_engine_v5.py#L2643-L2647) |
| `liquidity_quality` | 90/65/30/0 | حسب `sweep_quality`: STRONG/MODERATE/WEAK/NONE |
| `structure_strength` | 90/75/60/35/0 | CHoCH+BOS معاً/CHoCH فقط/BOS فقط/structure_grace/لا شي |
| `rr_score` | 100/85/65/45/0 | RR≥2.5/≥2.0/≥1.5/≥1.3/أقل |

**عقوبات** (تُطرح من raw): RR<1.5 (−10)، فريم ≤15m (−10)، structure معلّقة (−15)،
سوق RANGING (−5)، ضعف sweep (−4 إلى −10 حسب القوة)، تعارض zone (−8)، تعارض
HTF (متغير × multiplier)، TP/SL قريبين (−8 لكل واحد)، دخول بعيد عن zone (−6)،
دخول عميق بالـOB (−5)، لا sweep ولا structure إطلاقاً (−15).

**مكافأة**: +5 لو HTF متوافق تماماً (`gate_htf_aligned`)، بحد أقصى 90 ([L2760-2761](backend/app/services/ai_engine_v5.py#L2760-L2761)).

**سقوف نهائية**: 90% دايماً، 75% لو RR<2.0، **65% لو الفريم ≤15m** (السقف
الأخير هو الأصرم ويطبَّق دايماً بغض النظر عن باقي الحسابات).

### ⚠️ تأكيد: الثقة heuristic غير معايرة إحصائياً

مؤكَّد من قراءة الصيغة كاملة — **لا يوجد أي نقطة بالكود تربط "80% ثقة" برقم
فعلي من `winrate` التاريخي عند حساب الثقة نفسها**. `get_winrate()` **يُستخدَم
فعلاً**، بس بمكانين مختلفين تماماً عن حساب الثقة: (1) لتعديل الحد الأدنى
لـRR بقسم 5.4، و(2) لتخفيف/تشديد `required_delta` بالمعايرة التلقائية (قسم 4).
الثقة نفسها صيغة أوزان ثابتة (0.40/0.25/0.20/0.15) **لم تُعاير أبداً مقابل
نتائج فعلية** — يعني "confidence=80%" اليوم هو حكم هندسي مركّب (جودة الأدلة)،
مش احتمال إحصائي حقيقي بمعنى "80% من هالصفقات بتربح".

**هل فيه بيانات كافية لمعايرة حقيقية لاحقاً؟** نعم من ناحية الكمية (508+
صفقة محسومة بالسجل التاريخي)، لكن يحتاج عمل إضافي حقيقي: تجميع كل صفقة
محسومة بـ`confidence` وقتها مقابل النتيجة الفعلية (win/loss)، وبناء منحنى
معايرة (calibration curve) — هذا **غير موجود بالكود اليوم إطلاقاً**، لا يوجد
أي دالة تقرأ `ai_confidence` التاريخي وتقارنه بمعدل الربح الفعلي عند نفس
مستوى الثقة.

---

## 7. تحليل هندسي — نقاط القوة والضعف

**(رأي تقني بحت، ليس نصيحة استثمارية)**

### أقوى جزء بالاستراتيجية
**الـveto الصارم بلا استثناءات** (HTF، Zone، RR، Confluence 2/3، XAUUSD Rule 6) —
هندسياً هذا الأمتن جزء بالنظام لأنه **قابل للتحقق الحي 100%** (شفناه بأنفسنا
بتشخيصات سابقة: زوج delta=18 فوق العتبة انرفض بـzone_veto رغم قوته). العقوبات
الوزنية ممكن تتناقض أو تتراكم بشكل معقّد، بس القواعد الحمراء بسيطة، حتمية،
ومُختبرة فعلياً.

### أضعف جزء
**أوزان الثقة الأربعة (0.40/0.25/0.20/0.15) وكل نقاط قسم 2 (20/25/15/15/25/10/10/5/5)
أرقام مُصمَّمة يدوياً (heuristic)، لا معايرة إحصائية وراءها**. نفس الملاحظة
تنطبق على معامل الـ0.5×ATR لبناء الـSL (قسم 5.2) — رقم معقول هندسياً، بس
غير مُختبر إحصائياً ضد سلوك السوق الفعلي (بالضبط الفجوة يلي ظهرت بتشخيص
XAGUSD: SL منطقي هيكلياً بس ضيق نسبة للتقلب الفعلي بدون أي تحذير مخصص لهيك حالة).

### أين تنتهي "الاستراتيجية" وتبدأ "إدارة المخاطر التقنية"؟

خط فاصل واضح بالكود نفسه:

| الفئة | يشمل | أين |
|---|---|---|
| **الاستراتيجية** (تقرر شو نتداول ولوين) | كل شي بالقسمين 1-6 فوق: ICT concepts، Confluence، decision_finalizer، gates، confidence | `ict_engine.py` بالكامل + `ai_engine_v5.py` بالكامل |
| **إدارة المخاطر التقنية** (تقرر هل نُرسل/نحفظ الإشارة يلي القرار خرج فيها) | منع تكديس الصفقات (`_has_active_signal`)، قاطع سلسلة الخسائر (`_check_loss_streak_breaker`)، rate limiting/cooldown، منع التكرار (`signal_hash`)، إغلاق تلقائي (`expires_at`) | `bot.py` + `signals.py` — **خارج ai_engine_v5.py تماماً** |

الفصل عملياً نظيف: `ai_engine_v5.py::analyze_market()` بيرجّع قرار كامل
(BUY/SELL/WAIT + مستويات + ثقة) **بدون ما يعرف أصلاً إذا رح يُحفَظ إشارة
جديدة ولا لأ** — القرار بهيك محايد بالكامل عن حالة قاعدة البيانات الحالية
(هل فيه صفقة نشطة، هل المستخدم بخسارة متتالية). هذا تصميم صحي: أي تطوير
مستقبلي على "شو نتداول" (القسم 1-6) ما بيحتاج يلمس منطق "هل نرسل هالقرار
فعلياً" (`bot.py`)، والعكس صحيح.
