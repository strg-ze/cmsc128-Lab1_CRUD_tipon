from flask import Flask, render_template, request, redirect, url_for
from init_db import get_db_connection
import calendar
from datetime import date, datetime

app = Flask(__name__)

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
        'SELECT DISTINCT due_date FROM tasks WHERE due_date LIKE ? AND is_visible = 1', (month_prefix,)
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
    query = f'SELECT * FROM tasks WHERE is_visible = 1 AND {where_clause}'
    return conn.execute(query, params).fetchall()

## -------------- routes --------------
@app.route("/")
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
        upcoming_tasks = get_visible_tasks(conn, 'due_date > ?', (selected_date,))
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
        show_single_day=show_single_day
        )


@app.route("/tasks", methods=['GET', 'POST'])
def tasks():
    conn = get_db_connection()

    if request.method == 'POST':
        conn.execute(
            'INSERT INTO tasks (name, description, priority, due_date, time, tags, category)'
             'VALUES(?, ?, ?, ?, ?, ?, ?)',
            (
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
def delete_task(task_id):
    conn = get_db_connection()
    conn.execute('UPDATE tasks SET is_visible = 0 WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('tasks', deleted=task_id))


@app.route("/tasks/edit/<int:task_id>")
def edit_task(task_id):
    conn = get_db_connection()
    task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    all_tasks = get_visible_tasks(conn, '1=1', ())
    conn.close()
    return render_template("tasks.html", tasks=all_tasks, edit_task= task)


@app.route("/tasks/update/<int:task_id>", methods=['POST'])
def update_task(task_id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE tasks SET name = ?, description = ?, priority = ?, due_date = ?, time = ?, tags = ?, category = ? WHERE id = ?',
            (
                request.form['task-name'],
                request.form['description'],
                request.form['priority'],
                request.form['due-date'],
                request.form['time'],
                request.form['tags'],
                request.form['category'], 
                task_id          
            )
    )
    conn.commit()
    conn.close()
    return redirect(url_for('tasks'))


@app.route("/tasks/complete/<int:task_id>", methods=['POST'])
def complete_task(task_id):
    conn = get_db_connection()
    task = conn.execute('SELECT completed FROM tasks WHERE id = ?', (task_id,)).fetchone()
    new_status = 0 if task ['completed'] else 1
    conn.execute('UPDATE tasks SET completed = ? WHERE id = ?', (new_status, task_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('tasks'))


@app.route("/tasks/restore/<int:task_id>", methods=['POST'])
def undo_task(task_id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE tasks SET is_visible = 1 WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('tasks'))


    

@app.route("/calendar_page")
def calendar_page():
    return ("calendar page not available")

if __name__ == "__main__":
    app.run(debug=True)