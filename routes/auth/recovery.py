import hashlib

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature
from werkzeug.security import generate_password_hash

from init_db import get_db_connection
from routes.auth.validators import check_password
from routes.auth.mailer import send_reset_email

bp = Blueprint("recovery", __name__)

#------------helper functions ------------------------
def _serializer(): #signs and time-stamps tokens with secret_key
    #salt makes the tokens useless for anything else signed with the same key
    return URLSafeTimedSerializer(current_app.secret_key, salt="password-reset")

def password_fingerprint(password_hash): #digest of current has, stored inside token
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def make_reset_token(user):
    return _serializer().dumps(
        {"uid": user["id"], "fp": password_fingerprint(user["password_hash"])}
    )

def load_reset_user(conn, token): #returns the user a valid token belongs to
    try:
        data = _serializer().loads(token, max_age=current_app.config["RESET_MAX_AGE"])
    except BadSignature:             
        return None

    user = conn.execute(
        "SELECT id, password_hash FROM users WHERE id = ?", (data["uid"],)
    ).fetchone()

    if user is None or data["fp"] != password_fingerprint(user["password_hash"]):
        return None
    return user


#--------------routes--------------------------
@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if "user_id" in session:
        return redirect(url_for("account.profile"))

    error = None
    submitted = False

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            error = "Please enter your email address."
        else:
            conn = get_db_connection()
            user = conn.execute(
                "SELECT id, password_hash FROM users WHERE email = ?", (email,)
            ).fetchone()
            conn.close()

            if user:
                link = url_for("recovery.reset_password", token=make_reset_token(user), _external=True)
                send_reset_email(email, link)


            submitted = True

    return render_template("forgot_password.html", error=error, submitted=submitted)


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db_connection()
    try:
        user = load_reset_user(conn, token)
        if user is None:
            flash("This reset link is invalid or has expired. Please request a new one.", "error")
            return redirect(url_for("recovery.forgot_password"))

        errors = {}
        if request.method == "POST":
            new = request.form.get("new-password", "")
            confirm = request.form.get("confirm-password", "")

            if len(new) < 8:
                errors["password"] = "Password must be at least 8 characters."
            elif new != confirm:
                errors["confirm"] = "Passwords do not match."

            if not errors:
                #update stored hash to replace old password
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(new), user["id"]),
                )
                conn.commit()
                flash("Password updated. Please log in with your new password.", "success")
                return redirect(url_for("auth.login"))

        return render_template("reset_password.html", errors=errors, token=token)
    finally:
        conn.close()