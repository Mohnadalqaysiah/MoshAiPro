"""
عرض الهدف الأول كهدف تأمين (2026-11-12، 0.7R من 16/11): الاسم بوظيفته، والعائد حتى الهدف 2، وسطر الإرشاد — العربية والإنجليزية.

  cd backend && python tests/test_tp1_presentation.py      (أو pytest)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "telegram-bot"))

import messages as M  # noqa: E402
import messages_en as ME  # noqa: E402

LADDER = {"signal_type": "BUY", "market": "XAUUSD", "entry_price": 4000.0, "stop_loss": 3990.0,
          "take_profit_1": 4007.0, "take_profit_2": 4025.0, "take_profit_3": 4042.0}


def test_arabic_signal_names_tp1_and_shows_rr_to_tp2():
    t = M.signal_full(LADDER, "الذهب", "ساعة", 72)
    assert "🔒 الهدف 1 (تأمين)" in t and "+0.7R" in t                               # الرقم ظاهر لا مخفي
    assert "📐 العائد للمخاطرة حتى الهدف 2: <b>1:2.5</b>" in t
    assert "خذ جزءاً من الربح وانقل الوقف لنقطة الدخول" in t and "الهدف 3" in t
    assert t.index("الهدف 3") < t.index("📐")                                       # بعد كل الأهداف


def test_english_signal_mirrors():
    t = ME.signal_full(LADDER, "Gold", "1H", 72)
    assert "🔒 TP1 (secure)" in t and "+0.7R" in t and "📐 Risk/reward to TP2: <b>1:2.5</b>" in t
    assert "take partial profit and move your stop to entry" in t


def test_single_target_signal_has_no_rr_line():
    one = dict(LADDER, take_profit_2=4007.0, take_profit_3=None)
    assert "📐" not in M.signal_full(one, "الذهب", "ساعة", 70)
    assert "📐" not in ME.signal_full(one, "Gold", "1H", 70)


def test_other_bot_displays_label_tp1():
    src = (ROOT.parent / "telegram-bot" / "bot.py").read_text(encoding="utf-8")
    assert src.count("هدف 1 (تأمين)") == 2 and "TP1 (secure)" in src
    assert "✅ هدف 1:" not in src


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
