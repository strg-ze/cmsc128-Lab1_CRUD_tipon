from flask import Flask, render_template, request, redirect, url_for
from init_db import get_db_connection
import calendar
from datetime import date

app = Flask(__name__)

@app.route("/")
def dashboard():
    conn = get_db_connection()
    today = date.today()
    selected_date = request.args.get('date')

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(today.year, today.month)

    today_tasks = conn.execute(
        'SELECT * FROM tasks WHERE due_date = ? AND is_visible = 1', (today.isoformat(),)
    ).fetchall()

    if selected_date:
        upcoming_tasks = conn.execute(
            'SELECT * FROM tasks WHERE due_date = ? AND is_visible = 1', (selected_date,)
        ).fetchall()
        upcoming_label = selected_date
    else:
        upcoming_tasks = conn.execute(
            'SELECT * FROM tasks WHERE due_date > ? AND is_visible = 1', (today.isoformat(),)
        ).fetchall()
        upcoming_label = "Upcoming"


    month_prefix = today.strftime('%Y-%m') + '-%'
    task_dates_rows = conn.execute(
        'SELECT DISTINCT due_date FROM tasks WHERE due_date LIKE ? AND is_visible = 1', (month_prefix,)
    ).fetchall()

    task_days = set()
    for row in task_dates_rows:
        day_number = int(row['due_date'].split('-')[2])
        task_days.add(day_number)

        month_days_dates = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                full_date = date(today.year, today.month, day).isoformat()
                week_data.append({'day': day, 'date': full_date, 'has_tasks': day in task_days})
        month_days_dates.append(week_data)
    conn.close()
    
    return render_template(
        "dashboard.html", 
        today_tasks=today_tasks, 
        upcoming_tasks = upcoming_tasks,
        upcoming_label = upcoming_label,
        month_days_dates=month_days_dates,
        current_month=today.strftime('%B'),
        today_day=today.day
        )

@app.route("/tasks", methods=['GET', 'POST'])
def tasks():
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute(
            'INSERT INTO tasks (name, description, priority, due_date, time, tags, category) VALUES(?, ?, ?, ?, ?, ?, ?)',
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

    all_tasks = conn.execute('SELECT * FROM tasks WHERE is_visible = 1').fetchall()
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
    all_tasks = conn.execute('SELECT * FROM tasks WHERE is_visible = 1').fetchall()
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