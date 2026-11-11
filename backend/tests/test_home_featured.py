"""
مختارات المدونة بالرئيسية (2026-11-11): العنوان والتصنيف منسوخان من blogPosts.js ويجب أن يطابقاه حرفياً،
والروابط التسعة القديمة باقية، والأسئلة الخمسة موجودة، وصيغة الجمع لا تُكتب "{n} تحليلات" ثابتة.

  cd backend && python tests/test_home_featured.py      (أو pytest)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / "frontend/src/components/landing/landingV2Text.js").read_text(encoding="utf-8")
POSTS = (ROOT / "frontend/src/data/blogPosts.js").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend/src/pages/LandingV2.jsx").read_text(encoding="utf-8")


def _post(slug):
    i = POSTS.index(f"slug:     '{slug}'")
    block = POSTS[i:i + 3000]
    get = lambda k: re.search(rf"{k}:\s*'((?:[^'\\]|\\.)*)'", block).group(1)
    cat = re.search(r"category:\s*\{ ar: '([^']*)', en: '([^']*)' \}", block)
    return {"ar": get("titleAr"), "en": get("titleEn"), "catAr": cat.group(1), "catEn": cat.group(2)}


def _featured():
    body = TEXT[TEXT.index("export const FEATURED"):TEXT.index("export const COND_KEYS")]
    out = []
    for m in re.finditer(r"\{ slug: '([^']+)',(.*?)\},?\n", body, re.S):
        f = {"slug": m.group(1)}
        for k in ("ar", "en", "catAr", "catEn", "sumAr", "sumEn"):
            f[k] = re.search(rf"\b{k}: '((?:[^'\\]|\\.)*)'", m.group(2)).group(1)
        out.append(f)
    return out


def test_featured_titles_match_the_real_articles():
    fs = _featured()
    assert [f["slug"] for f in fs] == ["smart-money-concepts-smc-guide", "order-blocks-explained",
                                       "best-time-to-trade-gold", "ict-strategy-automation"]
    for f in fs:
        p = _post(f["slug"])
        for k in ("ar", "en", "catAr", "catEn"):
            assert f[k] == p[k], (f["slug"], k, f[k], p[k])
        for k in ("sumAr", "sumEn"):
            assert 40 < len(f[k]) < 200 and not re.search(r"مضمون|رابحة|guarantee|profit", f[k]), (f["slug"], k)


def test_old_internal_links_kept_and_all_articles_exist():
    blog = re.findall(r"\{ slug: '([^']+)', ar:", TEXT[TEXT.index("export const BLOG"):TEXT.index("export const FEATURED")])
    assert len(blog) == 9
    for slug in blog + [f["slug"] for f in _featured()]:
        assert f"slug:     '{slug}'" in POSTS, slug
    assert "BLOG.filter((b) => !FEATURED.some((f) => f.slug === b.slug))" in PAGE    # الباقي روابط صغيرة تحت البطاقات
    assert "to={isAr ? '/blog' : '/en/blog'}" in PAGE


def test_section_order_and_results_invite():
    order = [PAGE.index(m) for m in ('id="engine"', 'id="features"', 'id="builder"', 'id="learn"', 'id="reviews"',
                                     'className="results-line', 'id="pricing"', 'id="referral"', 'id="faq"', "── cta ──")]
    assert order == sorted(order)
    line = PAGE[PAGE.index('className="results-line'):PAGE.index('id="pricing"')]
    assert '<Link to="/results">' in line and not re.search(r"\d", line.split("<Link")[0])


def test_faq_and_trial_wording():
    ar = TEXT[TEXT.index("  ar: {\n    nav:"):TEXT.index("  en: {\n    nav:")]
    for q in ("هل الإشارات مضمونة الربح؟", "متى تُحسب الإشارة رابحة؟", "ما الأسواق المدعومة؟",
              "كيف يعمل ربط تيليجرام؟", "هل يتجدد الاشتراك تلقائياً؟"):
        assert q in ar, q
    assert "{n} تحليلات" not in TEXT and "{an}" in TEXT                      # الجمع يُحسب من العدد الحي
    assert "رمز QR" in ar and "ترفض" not in ar.split("heroLead:")[1].split("\n")[0]


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
