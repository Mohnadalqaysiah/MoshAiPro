"""
Qaffel AI — Email Service via Hostinger SMTP
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger


SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
SMTP_FROM = "support@qaffel.com"
SMTP_NAME = "Qaffel AI"


def send_email(to: str, subject: str, body_html: str, smtp_password: str) -> bool:
    """إرسال إيميل عبر Hostinger SMTP SSL"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{SMTP_NAME} <{SMTP_FROM}>"
        msg["To"]      = to

        msg.attach(MIMEText(body_html, "html", "utf-8"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
            server.login(SMTP_FROM, smtp_password)
            server.sendmail(SMTP_FROM, to, msg.as_string())

        logger.info(f"✉️  Email sent → {to} | {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Email failed → {to} | {e}")
        return False


def otp_email_body(otp: str) -> str:
    return f"""
    <div dir="rtl" style="font-family:Arial,sans-serif;max-width:520px;margin:auto;
         background:#111827;border-radius:16px;padding:32px;color:#e5e7eb;">
      <div style="text-align:center;margin-bottom:24px;">
        <div style="display:inline-block;background:#3b82f6;border-radius:12px;
             width:48px;height:48px;line-height:48px;font-size:22px;font-weight:bold;color:#fff;">Q</div>
        <h2 style="margin:12px 0 4px;color:#fff;">Qaffel AI</h2>
        <p style="margin:0;color:#9ca3af;font-size:14px;">استعادة كلمة المرور</p>
      </div>

      <p style="margin-bottom:8px;">مرحباً،</p>
      <p style="color:#9ca3af;margin-bottom:24px;">
        رمز التحقق الخاص باستعادة كلمة مرور حسابك:
      </p>

      <div style="background:#1f2937;border:2px solid #3b82f6;border-radius:14px;
           padding:24px;text-align:center;margin-bottom:24px;">
        <span style="font-size:40px;font-weight:bold;color:#3b82f6;
              letter-spacing:12px;font-family:monospace;">{otp}</span>
      </div>

      <p style="color:#6b7280;font-size:13px;text-align:center;">
        ⏱ صالح لمدة <strong style="color:#fbbf24;">10 دقائق</strong> فقط
        &nbsp;·&nbsp; لا تشاركه مع أحد
      </p>

      <hr style="border:none;border-top:1px solid #374151;margin:24px 0;">
      <p style="color:#4b5563;font-size:12px;text-align:center;margin:0;">
        إذا لم تطلب هذا الرمز، تجاهل هذا الإيميل.
        &nbsp;·&nbsp;
        <a href="https://qafeel.com" style="color:#3b82f6;text-decoration:none;">qafeel.com</a>
      </p>
    </div>
    """


_HEADER = """
<div dir="rtl" style="font-family:Arial,sans-serif;max-width:540px;margin:auto;
     background:#0f172a;border-radius:16px;overflow:hidden;color:#e5e7eb;">
  <div style="background:linear-gradient(135deg,#1e3a5f,#1e40af);padding:28px 32px;text-align:center;">
    <div style="display:inline-block;background:#3b82f6;border-radius:12px;
         width:52px;height:52px;line-height:52px;font-size:24px;font-weight:bold;color:#fff;">Q</div>
    <h1 style="margin:10px 0 0;color:#fff;font-size:20px;font-weight:700;">Qaffel AI</h1>
  </div>
  <div style="padding:28px 32px;">
"""

_FOOTER = """
  </div>
  <div style="background:#0a0f1e;padding:16px 32px;text-align:center;">
    <p style="color:#4b5563;font-size:12px;margin:0;">
      © 2025 Qaffel AI &nbsp;·&nbsp;
      <a href="https://qaffel.com" style="color:#3b82f6;text-decoration:none;">qaffel.com</a>
      &nbsp;·&nbsp;
      <a href="https://qaffel.com/dashboard" style="color:#3b82f6;text-decoration:none;">دخول للمنصة</a>
    </p>
  </div>
</div>
"""


def _btn(text: str, url: str, color: str = "#3b82f6") -> str:
    return f"""<div style="text-align:center;margin:24px 0;">
      <a href="{url}" style="background:{color};color:#fff;text-decoration:none;
         padding:13px 32px;border-radius:10px;font-weight:bold;font-size:15px;
         display:inline-block;">{text}</a>
    </div>"""


def welcome_email_body(name: str, trial_days: int = 7, trial_analyses: int = 10) -> str:
    first = name.split()[0] if name else "مستخدمنا العزيز"
    return _HEADER + f"""
    <h2 style="color:#fff;margin-top:0;">مرحباً بك في Qaffel AI 🎉</h2>
    <p style="color:#cbd5e1;">أهلاً <strong style="color:#93c5fd;">{first}</strong>،</p>
    <p style="color:#94a3b8;line-height:1.7;">
      تم إنشاء حسابك بنجاح. يمكنك الآن الاستمتاع بالفترة التجريبية المجانية:
    </p>
    <div style="background:#1e293b;border-radius:12px;padding:20px;margin:20px 0;">
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="color:#94a3b8;padding:8px 0;">⏱ مدة التجربة</td>
          <td style="color:#fff;text-align:left;font-weight:bold;">{trial_days} أيام</td>
        </tr>
        <tr>
          <td style="color:#94a3b8;padding:8px 0;">📊 تحليلات مجانية</td>
          <td style="color:#fff;text-align:left;font-weight:bold;">{trial_analyses} تحليل</td>
        </tr>
        <tr>
          <td style="color:#94a3b8;padding:8px 0;">💬 محادثات AI مجانية</td>
          <td style="color:#fff;text-align:left;font-weight:bold;">20 محادثة</td>
        </tr>
      </table>
    </div>
    {_btn("ابدأ الآن", "https://qaffel.com/dashboard")}
    <p style="color:#64748b;font-size:13px;text-align:center;">
      لأي استفسار تواصل معنا عبر support@qaffel.com
    </p>
    """ + _FOOTER


def payment_approved_email_body(name: str, plan: str, days: int, ends_at: str) -> str:
    first = name.split()[0] if name else "مستخدمنا العزيز"
    plan_label = "أسبوعي" if plan == "weekly" else "شهري"
    return _HEADER + f"""
    <h2 style="color:#22c55e;margin-top:0;">✅ تم تفعيل اشتراكك</h2>
    <p style="color:#cbd5e1;">مرحباً <strong style="color:#93c5fd;">{first}</strong>،</p>
    <p style="color:#94a3b8;line-height:1.7;">
      تم قبول دفعتك وتفعيل اشتراكك بنجاح. يمكنك الآن الاستمتاع بجميع مميزات المنصة.
    </p>
    <div style="background:#14532d;border:1px solid #16a34a;border-radius:12px;padding:20px;margin:20px 0;">
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="color:#86efac;padding:8px 0;">📦 نوع الاشتراك</td>
          <td style="color:#fff;text-align:left;font-weight:bold;">{plan_label}</td>
        </tr>
        <tr>
          <td style="color:#86efac;padding:8px 0;">📅 مدة الاشتراك</td>
          <td style="color:#fff;text-align:left;font-weight:bold;">{days} يوم</td>
        </tr>
        <tr>
          <td style="color:#86efac;padding:8px 0;">⏰ ينتهي في</td>
          <td style="color:#fbbf24;text-align:left;font-weight:bold;">{ends_at}</td>
        </tr>
      </table>
    </div>
    {_btn("دخول للمنصة", "https://qaffel.com/dashboard", "#16a34a")}
    """ + _FOOTER


def payment_rejected_email_body(name: str, plan: str, note: str = "") -> str:
    first = name.split()[0] if name else "مستخدمنا العزيز"
    plan_label = "أسبوعي" if plan == "weekly" else "شهري"
    note_section = f"""
    <div style="background:#450a0a;border:1px solid #dc2626;border-radius:10px;padding:14px;margin:16px 0;">
      <p style="color:#fca5a5;margin:0;font-size:13px;">ملاحظة الإدارة: {note}</p>
    </div>""" if note else ""
    return _HEADER + f"""
    <h2 style="color:#ef4444;margin-top:0;">❌ تعذّر قبول الدفعة</h2>
    <p style="color:#cbd5e1;">مرحباً <strong style="color:#93c5fd;">{first}</strong>،</p>
    <p style="color:#94a3b8;line-height:1.7;">
      للأسف لم نتمكن من التحقق من دفعتك للاشتراك <strong>{plan_label}</strong>.
      يرجى التواصل معنا أو إعادة المحاولة مع التأكد من صحة بيانات التحويل.
    </p>
    {note_section}
    {_btn("تواصل مع الدعم", "https://qaffel.com/contact", "#dc2626")}
    <p style="color:#64748b;font-size:13px;text-align:center;">
      support@qaffel.com
    </p>
    """ + _FOOTER


def subscription_expiry_email_body(name: str, days_left: int) -> str:
    first = name.split()[0] if name else "مستخدمنا العزيز"
    urgency_color = "#ef4444" if days_left <= 1 else "#f59e0b"
    urgency_text  = "ينتهي اليوم!" if days_left <= 1 else f"ينتهي خلال {days_left} أيام"
    return _HEADER + f"""
    <h2 style="color:{urgency_color};margin-top:0;">⚠️ اشتراكك على وشك الانتهاء</h2>
    <p style="color:#cbd5e1;">مرحباً <strong style="color:#93c5fd;">{first}</strong>،</p>
    <div style="background:#1c1917;border:1px solid {urgency_color};border-radius:12px;
         padding:20px;text-align:center;margin:20px 0;">
      <p style="color:{urgency_color};font-size:22px;font-weight:bold;margin:0;">{urgency_text}</p>
    </div>
    <p style="color:#94a3b8;line-height:1.7;">
      لا تنقطع عن إشاراتك اليومية — جدّد اشتراكك الآن واستمر في الاستفادة من تحليلات ICT الاحترافية.
    </p>
    {_btn("تجديد الاشتراك", "https://qaffel.com/subscription", urgency_color)}
    """ + _FOOTER


def affiliate_commission_email_body(
    name: str, commission_usd: float, referral_name: str,
    tier: int, pending_balance: float
) -> str:
    first = name.split()[0] if name else "صديقنا العزيز"
    return _HEADER + f"""
    <h2 style="color:#a78bfa;margin-top:0;">💰 حصلت على عمولة جديدة!</h2>
    <p style="color:#cbd5e1;">مرحباً <strong style="color:#93c5fd;">{first}</strong>،</p>
    <p style="color:#94a3b8;line-height:1.7;">
      اشترك <strong>{referral_name}</strong> الذي دعوته — وحصلت على عمولة فورية:
    </p>
    <div style="background:#1e1b4b;border:1px solid #7c3aed;border-radius:12px;padding:20px;margin:20px 0;">
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="color:#c4b5fd;padding:8px 0;">💵 العمولة المكتسبة</td>
          <td style="color:#a3e635;text-align:left;font-size:20px;font-weight:bold;">${commission_usd:.2f}</td>
        </tr>
        <tr>
          <td style="color:#c4b5fd;padding:8px 0;">🏆 مستواك</td>
          <td style="color:#fff;text-align:left;font-weight:bold;">Tier {tier}</td>
        </tr>
        <tr>
          <td style="color:#c4b5fd;padding:8px 0;">🏦 رصيدك الكلي</td>
          <td style="color:#fbbf24;text-align:left;font-weight:bold;">${pending_balance:.2f}</td>
        </tr>
      </table>
    </div>
    {_btn("عرض لوحة الأفلييت", "https://qaffel.com/profile", "#7c3aed")}
    """ + _FOOTER


def contact_email_body(name: str, sender_email: str, subject: str, message: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;
         background:#111827;border-radius:16px;padding:32px;color:#e5e7eb;">
      <h2 style="color:#3b82f6;margin-top:0;">رسالة جديدة — Qaffel AI</h2>
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="color:#9ca3af;padding:6px 0;width:120px;">الاسم:</td><td style="color:#fff;">{name}</td></tr>
        <tr><td style="color:#9ca3af;padding:6px 0;">البريد:</td><td style="color:#3b82f6;">{sender_email}</td></tr>
        <tr><td style="color:#9ca3af;padding:6px 0;">الموضوع:</td><td style="color:#fff;">{subject}</td></tr>
      </table>
      <hr style="border:none;border-top:1px solid #374151;margin:20px 0;">
      <p style="white-space:pre-wrap;color:#d1d5db;">{message}</p>
    </div>
    """
