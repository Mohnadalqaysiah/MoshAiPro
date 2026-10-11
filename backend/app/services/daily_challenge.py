"""
daily_challenge.py — تحدّي كفيل اليومي (2026-10-11)
====================================================
سؤال واحد كل يوم، نفسه لكل المشتركين (مولّد حتمياً من التاريخ)، يُرسل على
تيليجرام كاختبار Quiz. الإجابة الصحيحة تُضاف لنقاط الألعاب ولوحة المتصدّرين.

الأسئلة من نفس مادة الألعاب التعليمية (frontend/public/games/challenge.html):
مصطلحات ICT والتداول، ومسائل إدارة المخاطرة بنفس معادلاتها المراجَعة.
حدود تيليجرام: السؤال ≤ 300 حرف، كل خيار ≤ 100، الشرح ≤ 200.
"""
import random
from datetime import date

# (المستوى، المصطلح، التعريف) — مطابقة لقائمة ITEMS في صفحة الألعاب
TERMS = [
    (1, "Support", "مستوى سعري يتوقف عنده الهبوط غالبًا لأن المشترين يظهرون عنده."),
    (1, "Resistance", "مستوى سعري يتوقف عنده الصعود غالبًا لأن البائعين يظهرون عنده."),
    (1, "Stop Loss", "أمر يغلق الصفقة تلقائيًا عند سعر محدد ليحدّ من الخسارة."),
    (1, "Take Profit", "أمر يغلق الصفقة تلقائيًا عند سعر الهدف لتأمين الربح."),
    (1, "Spread", "الفرق بين سعر الشراء وسعر البيع، وهو تكلفة الدخول."),
    (1, "Lot", "وحدة قياس حجم الصفقة."),
    (1, "Timeframe", "المدة الزمنية التي تمثلها كل شمعة على الشارت."),
    (2, "BOS", "إغلاق شمعة خلف قمة أو قاع سابق، يؤكد استمرار الاتجاه."),
    (2, "CHoCH", "أول كسر هيكلي عكس الاتجاه السائد، يلمّح لاحتمال تغيّر الاتجاه."),
    (2, "FVG", "فجوة سعرية تتركها حركة اندفاعية بين ذيول ثلاث شموع متتالية."),
    (2, "Order Block", "آخر شمعة معاكسة قبل حركة اندفاعية قوية، منطقة دخول أوامر كبيرة."),
    (2, "Liquidity", "تجمع أوامر وقف الخسارة فوق القمم وتحت القيعان."),
    (2, "Liquidity Sweep", "اختراق سريع لمستوى سيولة ثم عودة السعر، لالتقاط أوامر الوقف."),
    (2, "Premium / Discount", "النصف الأعلى من النطاق علاوة تناسب البيع، والأدنى خصم يناسب الشراء."),
    (2, "Kill Zone", "نافذة زمنية يزداد فيها النشاط، مثل افتتاح لندن ونيويورك."),
    (2, "Retest", "عودة السعر لاختبار مستوى تم اختراقه سابقًا."),
    (3, "MSS", "تحوّل في هيكل السوق مصحوب باندفاع، يقوّي إشارة تغيّر الاتجاه."),
    (3, "Displacement", "حركة اندفاعية بشموع كبيرة متتالية تترك غالبًا FVG."),
    (3, "Breaker Block", "Order Block فشل وتم كسره، فيتحول إلى منطقة معاكسة."),
    (3, "OTE", "منطقة دخول مثالية بين تصحيح 0.62 و0.79."),
    (3, "Judas Swing", "حركة مضللة عند افتتاح الجلسة عكس الاتجاه الحقيقي لسحب السيولة."),
    (3, "Inducement", "قمة أو قاع صغير يستدرج المتداولين للدخول مبكرًا قبل الحركة الحقيقية."),
    (3, "Confluence", "تلاقي عدة أدلة مستقلة في نفس المنطقة لرفع احتمال نجاح الصفقة."),
    (3, "Expectancy", "متوسط ربح الصفقة الواحدة بوحدات R بعد احتساب الرابحة والخاسرة."),
]


def _usd(v: float) -> str:
    return f"${v:,.0f}" if float(v).is_integer() else f"${v:,.2f}"


def _fmt_r(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def _q_term(rnd: random.Random) -> dict:
    lvl, term, definition = rnd.choice(TERMS)
    pool = [t for t in TERMS if t[1] != term]
    wrong = [t[2] for t in rnd.sample(pool, 3)]
    opts = [definition] + wrong
    rnd.shuffle(opts)
    return {
        "question": f"🧠 ما معنى «{term}»؟",
        "options": opts,
        "correct": opts.index(definition),
        "explanation": f"{term}: {definition}",
    }


def _mcq(rnd, question, correct_txt, wrong_txts, explanation):
    seen, opts = {correct_txt}, [correct_txt]
    for w in wrong_txts:
        if w not in seen:
            seen.add(w)
            opts.append(w)
        if len(opts) == 4:
            break
    rnd.shuffle(opts)
    return {"question": question, "options": opts, "correct": opts.index(correct_txt), "explanation": explanation}


def _q_risk_amount(rnd):
    bal, pct = rnd.choice([1000, 2000, 5000, 10000]), rnd.choice([0.5, 1, 2])
    ans = bal * pct / 100
    return _mcq(rnd, f"💰 رصيدك {_usd(bal)} وتخاطر بـ {pct}% في الصفقة. كم تخسر لو ضُرب الوقف؟",
                _usd(ans), [_usd(bal * pct), _usd(bal * pct / 10), _usd(ans * 2), _usd(bal / pct)],
                f"المخاطرة = الرصيد × النسبة = {_usd(bal)} × {pct}% = {_usd(ans)}.")


def _q_rr(rnd):
    d, rr = rnd.choice([4, 5, 8, 10]), rnd.choice([1.5, 2, 2.5, 3])
    entry = round(rnd.uniform(4080, 4220), 1)
    sl, tp = round(entry - d, 1), round(entry + d * rr, 1)
    return _mcq(rnd, f"📐 شراء ذهب: الدخول {entry} · الوقف {sl} · الهدف {tp}. ما نسبة العائد إلى المخاطرة؟",
                f"1:{_fmt_r(rr)}", [f"1:{_fmt_r(round(10 / rr) / 10)}", f"1:{_fmt_r(rr + 1)}", f"1:{_fmt_r(rr * 2)}", "1:1"],
                f"المخاطرة {d} والربح {_fmt_r(d * rr)}، فالنسبة = الربح ÷ المخاطرة = 1:{_fmt_r(rr)}.")


def _q_breakeven(rnd):
    rr = rnd.choice([1, 1.5, 2, 3])
    ans = round(100 / (1 + rr))
    return _mcq(rnd, f"⚖️ تتداول بنسبة عائد إلى مخاطرة 1:{_fmt_r(rr)}. ما أقل نسبة نجاح تكفي للتعادل؟",
                f"{ans}%", [f"{round(100 / rr)}%", f"{round(100 * rr / (1 + rr))}%", "50%", f"{ans + 10}%"],
                f"نسبة التعادل = 1 ÷ (1 + {_fmt_r(rr)}) ≈ {ans}%. كلما ارتفعت RR قلّت النسبة اللازمة.")


def _q_net_r(rnd):
    w, rr = rnd.choice([3, 4, 5]), rnd.choice([2, 2.5, 3])
    l, net = 10 - w, w * rr - (10 - w)

    def s(v):
        return ("+" if v > 0 else "−" if v < 0 else "") + _fmt_r(abs(v)) + "R"
    return _mcq(rnd, f"📊 من 10 صفقات ربحت {w} وخسرت {l}، كل رابحة 1:{_fmt_r(rr)} وكل خاسرة 1R. كم الصافي؟",
                s(net), [s(w * rr), s(w - l), s(w * rr - l * rr), s(-net)],
                f"الصافي = ({w} × {_fmt_r(rr)}) − ({l} × 1) = {s(net)}. نسبة نجاح أقل من 50% قد تربح.")


def _q_drawdown(rnd):
    n, pct = rnd.choice([5, 8, 10]), rnd.choice([1, 2, 3])
    rem = 10000 * (1 - pct / 100) ** n
    return _mcq(rnd, f"📉 رصيدك $10,000 وتخاطر بـ {pct}% من الرصيد الحالي، وخسرت {n} صفقات متتالية. كم يتبقى تقريبًا؟",
                _usd(round(rem)), [_usd(round(10000 * (1 - n * pct / 100))), _usd(round(10000 * (1 - pct / 100) ** (n - 1))),
                                   _usd(round(10000 * (1 + pct / 100) ** n)), _usd(10000 - n * pct)],
                f"كل خسارة تُحسب من الرصيد المتبقي: 10,000 × {1 - pct / 100:.2f}^{n} ≈ {_usd(round(rem))}.")


_GENERATORS = [_q_term, _q_risk_amount, _q_term, _q_rr, _q_term, _q_breakeven, _q_net_r, _q_drawdown]


def build(day: date) -> dict:
    """سؤال اليوم — حتمي: نفس التاريخ يعطي نفس السؤال دائماً (لتصحيح الإجابة لاحقاً)."""
    rnd = random.Random(int(day.strftime("%Y%m%d")))
    q = _GENERATORS[day.toordinal() % len(_GENERATORS)](rnd)
    q["options"] = [o[:100] for o in q["options"]]
    q["question"] = q["question"][:300]
    q["explanation"] = q["explanation"][:200]
    q["id"] = day.isoformat()
    return q
