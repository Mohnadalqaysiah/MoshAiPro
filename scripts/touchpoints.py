"""
(2026-11-09) خريطة المواضع — كل معلومة تتكرر في أكثر من مكان، وأين تظهر بالضبط.

لماذا: تعديلات سابقة طالت مكاناً ونسيت آخر (مواعيد الأخبار صُلحت بالبوت وبقيت خاطئة بالداشبورد،
"هدفين" بقيت في مقالات بعد سلّم الثلاثة أهداف، 15m أُوقف بالخادم وبقي زره بالبوت).
السجل في docs/touchpoints.json: لكل معلومة كلمات بحث دقيقة + قائمة الملفات المعروفة.

  python scripts/touchpoints.py              فحص الكل: يكشف ملفاً جديداً غير مسجّل أو ملفاً مسجّلاً لم يعد يطابق
  python scripts/touchpoints.py prices       كل الأسطر التي تظهر فيها معلومة واحدة (قبل أي تعديل عليها)
  python scripts/touchpoints.py --list       أسماء المعلومات المسجّلة
  python scripts/touchpoints.py --sync prices   بعد المراجعة: اجعل قائمة الملفات = الواقع الحالي

قاعدة: قبل تعديل أي معلومة مسجّلة → شغّل الأمر باسمها وعدّل كل الأسطر الظاهرة، لا الملف الذي بيدك فقط.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs" / "touchpoints.json"

# خارج الفحص: التوثيق (يُذكر يدوياً في حقل docs)، والملفات المولّدة والثنائية، والخريطة نفسها.
EXCLUDE = [":!*.md", ":!docs/**", ":!**/package-lock.json", ":!*.lock", ":!**/dist/**",
           ":!*.png", ":!*.jpg", ":!*.webp", ":!*.ico", ":!*.woff2", ":!*.svg",
           ":!scripts/touchpoints.py"]


def load() -> list:
    return json.loads(MAP.read_text(encoding="utf-8"))["facts"]


def _grep(args: list) -> str:
    r = subprocess.run(["git", "grep", "--untracked", *args, "--", ".", *EXCLUDE], cwd=ROOT,
                       capture_output=True)
    if r.returncode not in (0, 1):                      # 1 = لا نتائج
        raise RuntimeError(r.stderr.decode("utf-8", "replace"))
    return r.stdout.decode("utf-8", "replace")


def _pattern_args(fact: dict) -> list:
    out = ["-I", "-E"]
    for p in fact["patterns"]:
        out += ["-e", p]
    return out


def files_now(fact: dict) -> set:
    return {l.strip() for l in _grep(["-l", *_pattern_args(fact)]).splitlines() if l.strip()}


def drift(fact: dict) -> tuple:
    known, now = set(fact["files"]), files_now(fact)
    return sorted(now - known), sorted(known - now)


def check(facts: list) -> int:
    bad = 0
    for f in facts:
        new, gone = drift(f)
        if not new and not gone:
            print(f"✓ {f['id']:<16} {len(f['files'])} ملف — {f['title']}")
            continue
        bad += 1
        print(f"✗ {f['id']:<16} {f['title']}")
        for x in new:
            print(f"    + ظهرت في ملف غير مسجّل: {x}")
        for x in gone:
            print(f"    − مسجّل ولم يعد يطابق:   {x}")
    if bad:
        print(f"\n{bad} معلومة تغيّرت مواضعها. راجع الملفات أعلاه (هل تحتاج نفس التعديل؟)، "
              f"ثم: python scripts/touchpoints.py --sync <id>")
    return bad


def show(fact: dict) -> None:
    print(f"== {fact['id']} — {fact['title']}\n{fact['note']}\n")
    for line in _grep(["-n", *_pattern_args(fact)]).splitlines():
        print("  " + (line if len(line) <= 220 else line[:220] + "…"))
    if fact.get("docs"):
        print("\nوتوثيق يُراجع يدوياً: " + "، ".join(fact["docs"]))
    if fact.get("guard"):
        print("حارس آلي: " + fact["guard"])


def sync(fact_id: str) -> None:
    data = json.loads(MAP.read_text(encoding="utf-8"))
    f = next(x for x in data["facts"] if x["id"] == fact_id)
    f["files"] = sorted(files_now(f))
    MAP.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"حُدّثت {fact_id}: {len(f['files'])} ملف")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    facts, args = load(), sys.argv[1:]
    if not args:
        return 1 if check(facts) else 0
    if args[0] == "--list":
        for f in facts:
            print(f"{f['id']:<16} {f['title']}")
        return 0
    if args[0] == "--sync" and len(args) == 2:
        sync(args[1])
        return 0
    by_id = {f["id"]: f for f in facts}
    if args[0] not in by_id:
        print("غير مسجّل. الأسماء: " + "، ".join(by_id))
        return 2
    show(by_id[args[0]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
