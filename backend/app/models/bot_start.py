"""
(2026-11-09) من ضغط Start في البوت بلا رابط ربط — قمع ربط تيليجرام (diag_link_funnel.py).

كان البوت يرد على هؤلاء "افتح المنصة واربط" ولا يُسجَّل شيء، فلا نعرف كم شخصاً جاء للبوت مباشرة
(بحث تيليجرام، القناة، "بوت تداول مجاني تليجرام" من قوقل) ولم يكن له حساب. هذا الرقم يحدد قيمة
"التسجيل من داخل البوت" قبل قرار المالك عليه.

صف واحد لكل حساب تيليجرام: أول/آخر ضغطة، وهل كان له حساب مربوط عند أول ضغطة.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class BotStart(Base):
    __tablename__ = "bot_starts"

    telegram_id = Column(String, primary_key=True)
    first_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    last_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    starts = Column(Integer, nullable=False, default=1)
    had_account = Column(Boolean, nullable=False, default=False)   # مربوط بحساب عند أول ضغطة
    lang = Column(String(8), nullable=True)
