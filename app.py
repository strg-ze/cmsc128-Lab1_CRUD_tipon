from flask import Flask, render_template, request, redirect, url_for, session, flash
from init_db import get_db_connection
import calendar
from datetime import date, datetime
#act2 imports
import re
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import hashlib
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask_mailman import Mail, EmailMessage
app = Flask(__name__)

load_dotenv()
app.secret_key = os.environ["SECRET_KEY"] 
serializer = URLSafeTimedSerializer(app.secret_key, salt="password-reset")
RESET_MAX_AGE = 15 * 60

app.config.update(
    MAIL_SERVER=os.environ.get("MAIL_SERVER"),
    MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
    MAIL_USE_TLS=True,                     
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
)
mail = Mail(app)


email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
# -------------- template filters --------------
@app.template_filter('format_date')
def format_date(value):
    if not value:
        return ''
    date_obj = datetime.strptime(value, '%Y-%m-%d')
    return date_obj.strftime('%B %d')

# -------------- helper functions --------------
def get_task_days_in_month(conn, year, month):
    month_prefix = f"{year}-{month:02d}-%"
    rows = conn.execute(
        'SELECT DISTINCT due_date FROM tasks WHERE due_date LIKE ? AND is_visible = 1 AND user_id=?' , (month_prefix, session["user_id"])
    ).fetchall()

    task_days = set()
    for row in rows:
        day_number = int(row['due_date'].split('-')[2])
        task_days.add(day_number)
    return task_days

def build_month_calendar(year, month, task_days):
    cal = calendar.Calendar(firstweekday=6)
    raw_weeks = cal.monthdayscalendar(year, month)

    weeks = []
    for week in raw_weeks:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                full_date = date(year, month, day).isoformat()
                week_data.append({'day': day, 'date': full_date, 'has_tasks': day in task_days})
        weeks.append(week_data)
    return weeks

def get_visible_tasks(conn, where_clause, params):
    query = f'SELECT * FROM tasks WHERE is_visible = 1 AND user_id = ? AND {where_clause}'
    return conn.execute(query, (session["user_id"],)+params).fetchall()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.after_request
def no_cache_for_logged_in_pages(response):
    if "user_id" in session:
        response.headers["Cache-Control"] = "no-store"
    return response

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

def password_fingerprint(password_hash):
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def make_reset_token(user):
    return serializer.dumps(
        {"uid": user["id"], "fp": password_fingerprint(user["password_hash"])}
    )


def load_reset_user(conn, token):
    try:
        data = serializer.loads(token, max_age=RESET_MAX_AGE)
    except BadSignature:             
        return None

    user = conn.execute(
        "SELECT id, password_hash FROM users WHERE id = ?", (data["uid"],)
    ).fetchone()

    if user is None or data["fp"] != password_fingerprint(user["password_hash"]):
        return None
    return user


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
        app.logger.error("Reset email failed: %s", exc)
## -------------- routes --------------
@app.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    errors = {}
    form = {}
    #clean entries
    display_name = request.form.get("display-name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password  = request.form.get("password", "")
    confirm = request.form.get("confirm-password", "")
    form = {"display_name": display_name, "email": email} 

    if not display_name:
        errors["email"] = "Please enter a display name."

    if not email:
        errors["email"] = "Please enter your email address"
    elif not email_pattern.fullmatch(email):
        errors["email"] = "Please enter a valid email address."

    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters."
    elif password != confirm:
        errors["confirm"] = "Passwords do not match."

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
                return redirect(url_for("login"))
        finally:
            conn.close()

    return render_template("register.html",
                           errors=errors,
                           form=form)

@app.route("/login", methods=["GET", "POST"])
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
                session.clear()
                session["user_id"] = user["id"]
                session["display_name"] = user["display_name"]
                return redirect(url_for("profile"))

    return render_template("login.html", errors=errors, email=email)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))
    
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    today = date.today()
    selected_date = request.args.get('date')

    today_tasks = get_visible_tasks(conn, 'due_date = ?', (today.isoformat(),))

    if selected_date:
        upcoming_tasks = get_visible_tasks(conn, 'due_date = ?', (selected_date,))
        upcoming_label = "Today" if selected_date == today.isoformat() else format_date(selected_date)
        show_single_day = True
    else:
        upcoming_tasks = get_visible_tasks(conn, 'due_date > ?', (today.isoformat(),))
        upcoming_label = "Upcoming"
        show_single_day = False

    task_days = get_task_days_in_month(conn, today.year, today.month)
    month_days_dates = build_month_calendar(today.year, today.month, task_days)
    conn.close()
    
    return render_template(
        "dashboard.html", 
        today_tasks=today_tasks, 
        upcoming_tasks = upcoming_tasks,
        upcoming_label = upcoming_label,
        month_days_dates=month_days_dates,
        current_month=today.strftime('%B'),
        today_day=today.day,
        show_single_day=show_single_day,
        display_name = session["display_name"]
        )


@app.route("/tasks", methods=['GET', 'POST'])
@login_required
def tasks():
    conn = get_db_connection()

    if request.method == 'POST':
        conn.execute(
            'INSERT INTO tasks (user_id, name, description, priority, due_date, time, tags, category)'
             'VALUES(?, ?, ?, ?, ?, ?, ?, ?)',
            (
                session["user_id"],
                request.form['task-name'],
                request.form['description'],
                request.form['priority'],
                request.form['due-date'],
                request.form['time'],
                request.form['tags'],
                request.form['category']            
            )
        )
        conn.commit()

    all_tasks = get_visible_tasks(conn, '1=1',())
    conn.close()
    return render_template("tasks.html", tasks = all_tasks)


@app.route("/tasks/delete/<int:task_id>", methods=['POST'])
@login_required
def delete_task(task_id):
    conn = get_db_connection()
    conn.execute('UPDATE tasks SET is_visible = 0 WHERE id = ? AND user_id=?', (task_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for('tasks', deleted=task_id))


@app.route("/tasks/edit/<int:task_id>")
@login_required
def edit_task(task_id):
    conn = get_db_connection()
    task = conn.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, session["user_id"])).fetchone()
    all_tasks = get_visible_tasks(conn, '1=1', ())
    conn.close()
    return render_template("tasks.html", tasks=all_tasks, edit_task= task)


@app.route("/tasks/update/<int:task_id>", methods=['POST'])
@login_required
def update_task(task_id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE tasks SET name = ?, description = ?, priority = ?, due_date = ?, time = ?, tags = ?, category = ? WHERE id = ? AND user_id=?',
            (
                request.form['task-name'],
                request.form['description'],
                request.form['priority'],
                request.form['due-date'],
                request.form['time'],
                request.form['tags'],
                request.form['category'], 
                task_id,
                session["user_id"]          
            )
    )
    conn.commit()
    conn.close()
    return redirect(url_for('tasks'))


@app.route("/tasks/complete/<int:task_id>", methods=['POST'])
@login_required
def complete_task(task_id):
    conn = get_db_connection()
    task = conn.execute('SELECT completed FROM tasks WHERE id = ? AND user_id = ?', (task_id, session["user_id"])).fetchone()
    new_status = 0 if task ['completed'] else 1
    conn.execute('UPDATE tasks SET completed = ? WHERE id = ? AND user_id = ?', (new_status, task_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('tasks'))


@app.route("/tasks/restore/<int:task_id>", methods=['POST'])
@login_required
def undo_task(task_id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE tasks SET is_visible = 1 WHERE id = ? AND user_id = ?', (task_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for('tasks'))

@app.route("/profile", methods=['GET'])
@login_required
def profile():
    conn = get_db_connection()
    user = get_current_user(conn)
    conn.close()
    return render_profile(user)
    

@app.route("/profile/details", methods=["POST"])
@login_required
def profile_details():
    display_name = request.form.get("display-name", "").strip()
    email = request.form.get("email", "").strip().lower()
    errors = {}

    if not display_name:
        errors["display_name"] = "Please enter a display name."
    if not email:
        errors["email"] = "Please enter your email address."
    elif not email_pattern.fullmatch(email):
        errors["email"] = "Please enter a valid email address"

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
                return redirect(url_for("profile"))
        return render_profile(
                user,
                details_errors=errors,
                form={"display_name": display_name, "email": email},
            )
    finally:
        conn.close()

@app.route("/profile/password", methods=["POST"])
@login_required
def profile_password():
    current = request.form.get("current-password", "")
    new = request.form.get("new-password", "")
    confirm = request.form.get("confirm-password", "")
    errors = {}

    conn = get_db_connection()
    try:
        user = get_current_user(conn)
        if user is None:
            session.clear()
            return redirect(url_for("login"))

        if not check_password_hash(user["password_hash"], current):
            errors["current"] = "Current password is incorrect."

        if len(new) < 8:
            errors["new"] = "New password must be at least 8 characters."
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
            return redirect(url_for("profile"))

        return render_profile(user, password_errors=errors)
    finally:
        conn.close()

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if "user_id" in session:
        return redirect(url_for("profile"))

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
                link = url_for("reset_password", token=make_reset_token(user), _external=True)
                send_reset_email(email, link)


            submitted = True

    return render_template("forgot_password.html", error=error, submitted=submitted)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db_connection()
    try:
        user = load_reset_user(conn, token)
        if user is None:
            flash("This reset link is invalid or has expired. Please request a new one.", "error")
            return redirect(url_for("forgot_password"))

        errors = {}
        if request.method == "POST":
            new = request.form.get("new-password", "")
            confirm = request.form.get("confirm-password", "")

            if len(new) < 8:
                errors["password"] = "Password must be at least 8 characters."
            elif new != confirm:
                errors["confirm"] = "Passwords do not match."

            if not errors:
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(new), user["id"]),
                )
                conn.commit()
                flash("Password updated. Please log in with your new password.", "success")
                return redirect(url_for("login"))

        return render_template("reset_password.html", errors=errors, token=token)
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)