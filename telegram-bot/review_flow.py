"""
review_flow.py (2026-10-24) — إرسال رأي من البوت بنص وصورة/فيديو (طلب المالك: تقييمات العملاء دون حسابه الشخصي).

حالة نقية بلا telegram ولا شبكة — bot.py يمرّر المدخلات ويعرض الردود؛ الباكيند (/bot/reviews) يعيد كل الفحوص وهو المرجع.
الخطوات: النجوم ← صورة/فيديو (اختياري) ← النص ← الموافقة (باسمي / بدون اسمي). إلغاء بأي خطوة.
الشروط من نظام التقييمات (DECISIONS 17/10): مشترك مدفوع ≥7 أيام، موافقة صريحة على النشر، اعتماد الأدمن، لا يُرفض لسلبيته.
"""
MIN_TEXT = 20
MIN_TEXT_WITH_MEDIA = 5      # الصورة/الفيديو هي الرأي — يكفي تعليق قصير
MAX_TEXT = 600
VIDEO_MAX_MB = 20            # حد getFile بواجهة البوت — أكبر منه لا يمكن للأدمن معاينته

ASK_MEDIA = ("📸 أرفق <b>صورة أو فيديو قصير</b> إن أحببت (مثلاً لقطة شاشة لصفقة)\n"
             "أو اضغط <b>تخطّي</b>.")
ASK_TEXT = "✍️ اكتب رأيك بكلماتك — ما الذي أعجبك أو لم يعجبك؟ ({min}–{max} حرف)"
ASK_CONSENT = ("آخر خطوة: الرأي يُنشر بعد مراجعة الفريق في <b>الموقع وقناة Qaffel</b>.\n"
               "كيف تحب أن يظهر؟")
THANKS = ("🙏 <b>وصل رأيك، شكراً لك!</b>\n"
          "يظهر بعد مراجعة الفريق. الرأي السلبي يُنشر أيضاً — نرفض فقط الإساءة أو البيانات الشخصية.")
CANCELLED = "تم الإلغاء."


class ReviewFlow:
    def __init__(self):
        self.s: dict = {}

    def active(self, uid) -> bool:
        return uid in self.s

    def step(self, uid):
        return self.s.get(uid, {}).get("step")

    def start(self, uid):
        self.s[uid] = {"step": "rating"}

    def cancel(self, uid):
        self.s.pop(uid, None)
        return CANCELLED

    def on_rating(self, uid, n: int):
        if self.step(uid) != "rating" or not 1 <= int(n) <= 5:
            return None
        self.s[uid].update(step="media", rating=int(n))
        return ASK_MEDIA

    def _to_text(self, uid):
        self.s[uid]["step"] = "text"
        lo = MIN_TEXT_WITH_MEDIA if self.s[uid].get("file_id") else MIN_TEXT
        return ASK_TEXT.format(min=lo, max=MAX_TEXT)

    def on_media(self, uid, kind: str, file_id: str, size_bytes: int = 0):
        """يُرجع (نجح؟، الرد)."""
        if self.step(uid) != "media":
            return False, None
        if kind not in ("photo", "video"):
            return False, "أرسل صورة أو فيديو فقط، أو اضغط تخطّي."
        if kind == "video" and size_bytes and size_bytes > VIDEO_MAX_MB * 1024 * 1024:
            return False, f"الفيديو أكبر من {VIDEO_MAX_MB} ميغابايت — أرسل مقطعاً أقصر، أو اضغط تخطّي."
        self.s[uid].update(media_type=kind, file_id=file_id)
        return True, self._to_text(uid)

    def on_skip(self, uid):
        if self.step(uid) != "media":
            return None
        return self._to_text(uid)

    def on_text(self, uid, text: str):
        """يُرجع (نجح؟، الرد)."""
        if self.step(uid) != "text":
            return False, None
        t = (text or "").strip()
        lo = MIN_TEXT_WITH_MEDIA if self.s[uid].get("file_id") else MIN_TEXT
        if not lo <= len(t) <= MAX_TEXT:
            return False, f"النص بين {lo} و{MAX_TEXT} حرف — عندك {len(t)}. اكتبه مرة أخرى."
        self.s[uid].update(step="consent", text=t)
        return True, ASK_CONSENT

    def on_consent(self, uid, anonymous: bool):
        """يُرجع حمولة /bot/reviews ويُنهي الحالة، أو None."""
        st = self.s.get(uid)
        if not st or st.get("step") != "consent":
            return None
        self.s.pop(uid, None)
        return {"rating": st["rating"], "text": st["text"], "media_type": st.get("media_type"),
                "media_file_id": st.get("file_id"), "anonymous": bool(anonymous), "consent": True}
