"""
خريطة المواضع (2026-11-09): يفشل إذا ظهرت معلومة مسجّلة في ملف جديد، أو اختفت من ملف مسجّل،
حتى لا يُعدَّل مكان ويُنسى آخر. التفاصيل: python scripts/touchpoints.py

  cd backend && python tests/test_touchpoints.py      (أو pytest)
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("touchpoints", ROOT / "scripts" / "touchpoints.py")
TP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(TP)


def test_registry_is_well_formed():
    facts = TP.load()
    ids = [f["id"] for f in facts]
    assert len(ids) == len(set(ids)), "اسم مكرر"
    for f in facts:
        assert f["title"] and f["note"] and f["patterns"], f["id"]
        assert f["files"], f"{f['id']}: لا ملفات — هل الكلمات صحيحة؟"


def test_no_unregistered_or_missing_touchpoints():
    problems = {f["id"]: TP.drift(f) for f in TP.load()}
    problems = {k: v for k, v in problems.items() if v[0] or v[1]}
    assert not problems, (
        "تغيّرت مواضع معلومات مسجّلة — راجع كل ملف (هل يحتاج نفس التعديل؟) ثم "
        "python scripts/touchpoints.py --sync <id>:\n"
        + "\n".join(f"  {k}: جديد={new} مفقود={gone}" for k, (new, gone) in problems.items()))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✓", name)
    print(f"{n}/{n} passed")
