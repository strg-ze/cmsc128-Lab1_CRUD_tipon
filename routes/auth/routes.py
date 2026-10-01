import sqlite3

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from init_db import get_db_connection
from .validators import check_email, check_password

bp = Blueprint("auth", __name__)   # endpoints -> auth.login, auth.register

@bp.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    errors = {}
    form = {}

    if request.method == "POST":
    #clean entries
        display_name = request.form.get("display-name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password  = request.form.get("password", "")
        confirm = request.form.get("confirm-password", "")
        form = {"display_name": display_name, "email": email} 

        #validate
        if not display_name:
            errors["display_name"] = "Please enter a display name."

        email_error = check_email(email)
        if email_error:
            errors["email"] = email_error

        password_error = check_password(password)
        if password_error:
            errors["password"] = password_error
        elif password != confirm:
            errors["confirm"] = "Passwords do not match."

        #check duplicates
        if not errors:
            conn = get_db_connection()
            try:
                taken = conn.execute(
                    "SELECT id FROM users WHERE email = ?", (email,)
                ).fetchone()

                if taken:
                    errors["email"] = "An account with this email already exists."
                else:
                    conn.execute(
                        "INSERT INTO users (email, display_name, password_hash)"
                        "VALUES (?, ?, ?)",
                        (email, display_name, generate_password_hash(password)),
                    )
                    conn.commit()
                    flash("Account created! You can now log in.", "success")
                    return redirect(url_for("auth.login"))
            finally:
                conn.close()

    return render_template("register.html",
                           errors=errors,
                           form=form)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    errors = {}
    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email:
            errors["email"] = "Please enter your email address"
        if not password:
            errors["password"] = "Please enter your password"

        if not errors:
            conn = get_db_connection()
            user = conn.execute(
                "SELECT id, display_name, password_hash FROM users WHERE email = ?", (email,),
            ).fetchone()
            conn.close()

            if user is None or not check_password_hash(user["password_hash"], password):
                errors["form"] = "Invalid email or password."
            else:
                session.clear() #start from a fresh session
                session["user_id"] = user["id"] #logged in marker
                session["display_name"] = user["display_name"]
                return redirect(url_for("account.profile"))

    return render_template("login.html", errors=errors, email=email)

@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))