import os
from flask import current_app
from flask_mailman import EmailMessage


def send_reset_email(to_email, link):
    body = (
        "We received a request to reset your password. To continue managing your tasks smoothly click the link below to enter a new password. \n"
        f"\n{link}\n\n"
        "This link will expire in 15 minutes. \n\n"
        "Sincerely, \n"
        "Agenda"
    )
    try:
        EmailMessage(
            subject="Reset your Agenda password",
            body=body,
            from_email=os.environ.get("MAIL_SENDER"),
            to=[to_email],
        ).send()
    except Exception as exc:
        current_app.logger.error("Reset email failed: %s", exc)