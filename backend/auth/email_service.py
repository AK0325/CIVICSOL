import smtplib
from email.message import EmailMessage

from ..core.config import settings


def send_otp_email(
    recipient_email: str,
    otp: str,
) -> bool:

    message = EmailMessage()

    message["Subject"] = "CIVICSOL Password Reset OTP"
    message["From"] = (
        f"{settings.SMTP_FROM_NAME} "
        f"<{settings.SMTP_FROM_EMAIL}>"
    )
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

We received a request to reset your CIVICSOL account password.

Your verification code is:

{otp}

This OTP is valid for 10 minutes.

If you did not request a password reset, you can safely ignore this email.

Regards,
CIVICSOL
Civic Intelligence Platform
""".strip()
    )

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
        ) as smtp:

            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()

            smtp.login(
                settings.SMTP_USERNAME,
                settings.SMTP_PASSWORD,
            )

            smtp.send_message(message)

        print(
            f"CIVICSOL: Password reset OTP email sent to "
            f"{recipient_email}"
        )

        return True

    except Exception as error:
        print(f"CIVICSOL EMAIL ERROR: {error}")
        return False
    