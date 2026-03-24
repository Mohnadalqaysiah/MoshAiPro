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
