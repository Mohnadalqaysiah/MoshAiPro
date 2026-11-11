"""
result_share_flow.py (2026-11-11) — "📸 شارك نتيجتك": لقطة شاشة لربح أو نتيجة تصل المالك مباشرة (طلب المالك).

حالة نقية بلا telegram ولا شبكة، بنفس أسلوب review_flow.py — bot.py يمرّر المدخلات ويعرض الردود، والخادم
(/bot/result-share) يعيد الفحوص ويرسل الصورة للمالك (services/result_shares.py).
الخطوات: الصورة (مع وصف اختياري) ← اختيار النشر: باسمي / بدون اسمي / للفريق فقط. إلغاء بأي خطوة.
"""
ASK_PHOTO = ("📸 أرسل <b>لقطة شاشة لنتيجتك</b> — ربح، أو صفقة من إشاراتنا، أو حسابك.\n"
             "صورة واحدة في كل مرة، ويمكنك كتابة وصف قصير مع الصورة.\n"
             "<i>أخفِ رقم حسابك وأي بيانات خاصة قبل الإرسال.</i>")
ASK_CONSENT = "شكراً! هل تسمح بنشرها في <b>قناة Qaffel</b>؟"
THANKS = ("🙏 <b>وصلت لقطتك، شكراً لك!</b>\n"
          "وصلت مباشرة لفريق Qaffel، ولن تُنشر إلا حسب اختيارك.")
ONLY_PHOTO = "أرسل صورة فقط (لقطة شاشة)، أو اضغط إلغاء."
PICK_CONSENT = "اختر طريقة النشر من الأزرار."
CANCELLED = "تم الإلغاء."

EN = {
    "ASK_PHOTO": ("📸 Send a <b>screenshot of your result</b>: a profit, a trade from our signals, or your account.\n"
                  "One image at a time; you can add a short caption with it.\n"
                  "<i>Hide your account number and any private data before sending.</i>"),
    "ASK_CONSENT": "Thank you! May we publish it in the <b>Qaffel channel</b>?",
    "THANKS": "🙏 <b>Got your screenshot, thank you!</b>\nIt went straight to the Qaffel team and is only published as you chose.",
    "ONLY_PHOTO": "Send an image only (a screenshot), or tap Cancel.",
    "PICK_CONSENT": "Choose how to publish from the buttons.",
    "CANCELLED": "Cancelled.",
}

CONSENT_KEYS = {"rs_c_name": "name", "rs_c_anon": "anon", "rs_c_private": "private"}


class ShareFlow:
    def __init__(self):
        self.s: dict = {}

    def active(self, uid) -> bool:
        return uid in self.s

    def step(self, uid):
        return self.s.get(uid, {}).get("step")

    def lang(self, uid) -> str:
        return self.s.get(uid, {}).get("lang", "ar")

    def _t(self, uid, key: str) -> str:
        return EN[key] if self.lang(uid) == "en" else globals()[key]

    def start(self, uid, lang: str = "ar") -> str:
        self.s[uid] = {"step": "photo", "lang": lang}
        return self._t(uid, "ASK_PHOTO")

    def cancel(self, uid) -> str:
        txt = self._t(uid, "CANCELLED")
        self.s.pop(uid, None)
        return txt

    def on_image(self, uid, kind: str, file_id: str, caption: str = ""):
        """يُرجع (نجح؟، الرد). kind: photo أو document (ملف صورة)."""
        if self.step(uid) != "photo":
            return False, self._t(uid, "PICK_CONSENT") if self.active(uid) else None
        if kind not in ("photo", "document") or not file_id:
            return False, self._t(uid, "ONLY_PHOTO")
        self.s[uid].update(step="consent", file_kind=kind, file_id=file_id, caption=(caption or "").strip())
        return True, self._t(uid, "ASK_CONSENT")

    def hint(self, uid):
        return {"photo": self._t(uid, "ONLY_PHOTO"), "consent": self._t(uid, "PICK_CONSENT")}.get(self.step(uid))

    def on_consent(self, uid, data: str):
        """يُرجع الحمولة للخادم ويُنهي الخطوات، أو None إن لم تكن بخطوة الموافقة."""
        if self.step(uid) != "consent" or data not in CONSENT_KEYS:
            return None
        st = self.s.pop(uid)
        return {"file_kind": st["file_kind"], "file_id": st["file_id"], "caption": st["caption"],
                "consent": CONSENT_KEYS[data]}
