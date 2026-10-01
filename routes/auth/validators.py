import re

email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
min_password_len = 8

def check_email(email):
    if not email:
        return "Please enter your email address."
    if not email_pattern.fullmatch(email):
        return "Please enter a valid email address."
    return None

def check_password(password):
    if len(password) < min_password_len:
        return f"Password must be at least {min_password_len} characters."
    return None