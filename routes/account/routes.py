import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from init_db import get_db_connection
from routes.auth.decorators import login_required
from routes.auth.validators import check_email, check_password

bp = Blueprint("account", __name__)

#---------------helper functions-----------------
def get_current_user(conn):
    return conn.execute(
        "SELECT id, email, display_name, password_hash FROM users WHERE id = ?", (session["user_id"],),
    ).fetchone()

def render_profile(user, details_errors=None, password_errors=None, form=None):
    return render_template (
        "profile.html",
        form=form or {"display_name": user["display_name"], "email": user["email"]},
        details_errors=details_errors or {},
        password_errors=password_errors or {}
    )

#------------routes-----------------------
@bp.route("/profile", methods=['GET'])
@login_required
def profile():
    conn = get_db_connection()
    user = get_current_user(conn)
    conn.close()
    return render_profile(user)
    

@bp.route("/profile/details", methods=["POST"])
@login_required
def profile_details():
    display_name = request.form.get("display-name", "").strip()
    email = request.form.get("email", "").strip().lower()
    errors = {}

    if not display_name:
        errors["display_name"] = "Please enter a display name."
    email_error = check_email(email)
    if email_error:
        errors["email"] = email_error
   
    conn = get_db_connection()
    try:
        user = get_current_user(conn)
        if not errors:
            other = conn.execute(
                "SELECT id FROM users WHERE email = ? AND id != ?", (email, user["id"])
            ).fetchone()
            if other:
                errors["email"] = "Another account already uses this email."

        if not errors:
                conn.execute(
                    "UPDATE users SET email = ?, display_name = ? WHERE id = ?",
                    (email, display_name, user["id"]),
                )
                conn.commit()
                session["display_name"] = display_name 
                flash("Profile updated.", "success")
                return redirect(url_for("account.profile"))
        return render_profile(
                user,
                details_errors=errors,
                form={"display_name": display_name, "email": email},
            )
    finally:
        conn.close()

@bp.route("/profile/password", methods=["POST"])
@login_required
def profile_password():
    current = request.form.get("current-password", "")
    new = request.form.get("new-password", "")
    confirm = request.form.get("confirm-password", "")
    errors = {}

    conn = get_db_connection()
    try:
        user = get_current_user(conn)

        if not check_password_hash(user["password_hash"], current):
            errors["current"] = "Current password is incorrect."

        password_error = check_password(new)
        if password_error:
            errors["new"] = password_error
        elif new == current:
            errors["new"] = "New password must be different from the current one."
        elif new != confirm:
            errors["confirm"] = "Passwords do not match."

        if not errors:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(new), user["id"]),  
            )
            conn.commit()
            flash("Password changed.", "success")
            return redirect(url_for("account.profile"))

        return render_profile(user, password_errors=errors)
    finally:
        conn.close()