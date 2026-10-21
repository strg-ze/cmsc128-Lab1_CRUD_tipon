import calendar
from datetime import date, datetime

from flask import Flask, render_template, request, redirect, url_for, session, abort

from init_db import get_db_connection

from routes.extensions import mail
from routes.auth.decorators import login_required, no_cache_for_logged_in_pages
from routes.auth.routes import bp as auth_bp
from routes.auth.recovery import bp as recovery_bp
from routes.account.routes import bp as account_bp
from routes.lists.routes import bp as lists_bp
from routes.lists.service import (
    get_personal_list_id, get_categories, get_own_category_or_404, parse_category_id, get_group_lists, get_group_list_or_404, get_members,
    get_task_for_user, get_tasks_for_view
)



app = Flask(__name__)
app.config.from_object("routes.config") #loads config variables
mail.init_app(app)
app.register_blueprint(lists_bp)
#-------act 2 auth features-------------
app.after_request(no_cache_for_logged_in_pages)
app.register_blueprint(auth_bp)
app.register_blueprint(recovery_bp)
app.register_blueprint(account_bp)


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
        """SELECT DISTINCT t.due_Date
            FROM tasks t
            JOIN list_members m ON m.list_id = t.list_id AND m.user_id = ?
            WHERE t.due_date LIKE ? AND t.is_visible = 1""",
            (session["user_id"], month_prefix),
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
        query = f"""SELECT t.*, c.name AS category,
                       CASE WHEN l.is_personal = 0 THEN l.name END AS list_name
                FROM tasks t
                JOIN lists l ON l.id = t.list_id
                JOIN list_members m ON m.list_id = l.id AND m.user_id = ?
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.is_visible = 1 AND {where_clause}"""
        return conn.execute(query, (session["user_id"],) + params).fetchall()

## -------------- routes --------------
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

def current_view():
    mode = "group" if request.args.get("mode") == "group" else "individual"
    param = "list" if mode == "group" else "page"
    selected = request.args.get(param, "")
    if not selected.isdigit():
        selected = ""
    return mode, param, selected


def view_args(mode, param, selected):
    # carried on every form action so a redirect lands back on the same view.
    return {"mode": mode, param: selected} if selected else {"mode": mode}


@app.route("/tasks", methods=['GET', 'POST'])
@login_required
def tasks():
    user_id = session["user_id"]
    mode, param, selected = current_view()
    view = view_args(mode, param, selected)

    conn = get_db_connection()
    try:

        if request.method == "POST":
            if mode == "group":
                raw = request.form.get("list_id", "")
                if not raw.isdigit():
                    abort(404)
                target_list = get_group_list_or_404(conn, int(raw), user_id)["id"]
                category_id = None # group tasks have no category
            else:
                target_list = get_personal_list_id(conn, user_id)
                category_id = parse_category_id(conn, user_id, request.form.get("category_id", ""))

            conn.execute(
                "INSERT INTO tasks (list_id, user_id, category_id, name, description, "
                "priority, due_date, time, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    target_list,
                    user_id,                         
                    category_id,
                    request.form['task-name'],
                    request.form['description'],
                    request.form['priority'],
                    request.form['due-date'],
                    request.form['time'],
                    request.form['tags'],
                ),
            )
            conn.commit()
            return redirect(url_for("tasks", **view))   # redirect after POST

        #show page
        categories = get_categories(conn, user_id)
        group_lists = get_group_lists(conn, user_id)

        if mode == "group":
            options = [{"value": str(l["id"]), "label": l["name"]} for l in group_lists]
        else:
            options = [{"value": str(c["id"]), "label": c["name"]} for c in categories]

        current = next((o for o in options if o["value"] == selected), None)
        if selected and current is None:
            abort(404)

        members, is_owner = [], False
        if mode == "group" and selected:
            lst = next(l for l in group_lists if str(l["id"]) == selected)
            is_owner = lst["owner_id"] == user_id
            members = get_members(conn, int(selected))

        edit_task = None
        edit_id = request.args.get("edit", "")
        if edit_id:
            if not edit_id.isdigit():
                abort(404)
            edit_task = get_task_for_user(conn, int(edit_id), user_id)
            if edit_task is None:
                abort(404)

        return render_template(
            "tasks.html",
            mode=mode, param=param, selected=selected, view=view,
            options=options, current_name=current["label"] if current else "",
            tasks=get_tasks_for_view(conn, user_id, mode, selected),
            categories=categories, members=members, is_owner=is_owner,
            edit_task=edit_task,
        )
    finally:
        conn.close()



@app.route("/tasks/delete/<int:task_id>", methods=['POST'])
@login_required
def delete_task(task_id):
    mode, param, selected = current_view()
    conn = get_db_connection()
    try:
        if get_task_for_user(conn, task_id, session["user_id"]) is None:
            abort(404)
        conn.execute("UPDATE tasks SET is_visible = 0 WHERE id = ?", (task_id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("tasks", deleted=task_id, **view_args(mode, param, selected)))



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
    user_id = session["user_id"]
    mode, param, selected = current_view()
    conn = get_db_connection()
    try:
        task = get_task_for_user(conn, task_id, user_id)
        if task is None:
            abort(404)

        category_id = None
        if task["is_personal"]:
            category_id = parse_category_id(conn, user_id, request.form.get("category_id", ""))

        conn.execute(
            "UPDATE tasks SET name = ?, description = ?, priority = ?, due_date = ?, "
            "time = ?, tags = ?, category_id = ? WHERE id = ?",
            (
                request.form['task-name'], request.form['description'],
                request.form['priority'], request.form['due-date'],
                request.form['time'], request.form['tags'],
                category_id, task_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("tasks", **view_args(mode, param, selected)))


@app.route("/tasks/complete/<int:task_id>", methods=['POST'])
@login_required
def complete_task(task_id):
    conn = get_db_connection()
    try:
        task = get_task_for_user(conn, task_id, session["user_id"])
        if task is None:
            abort(404)
        conn.execute("UPDATE tasks SET completed = ? WHERE id = ?",
                     (0 if task["completed"] else 1, task_id))
        conn.commit()
    finally:
        conn.close()
    return redirect(request.referrer or url_for("tasks"))



@app.route("/tasks/restore/<int:task_id>", methods=['POST'])
@login_required
def undo_task(task_id):
    mode, param, selected = current_view()
    conn = get_db_connection()
    try:
        if get_task_for_user(conn, task_id, session["user_id"]) is None:
            abort(404)
        conn.execute("UPDATE tasks SET is_visible = 1 WHERE id = ?", (task_id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("tasks", **view_args(mode, param, selected)))

if __name__ == "__main__":
    app.run(debug=True)