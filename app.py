from flask import Flask, render_template, request
from init_db import get_db_connection
from datetime import date

app = Flask(__name__)

@app.route("/")
def dashboard():
    conn = get_db_connection()
    today = date.today().isoformat()

    today_tasks = conn.execute(
        'SELECT * FROM tasks WHERE due_date = ? AND is_visible = 1', (today,)
    ).fetchall()

    upcoming_tasks = conn.execute(
        'SELECT * FROM tasks WHERE due_date > ? AND is_visible = 1', (today,)
    ).fetchall()

    conn.close()
    
    return render_template("dashboard.html", today_tasks=today_tasks, upcoming_tasks = upcoming_tasks)

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

@app.route("/calendar")
def calendar():
    return ("calendar page not available")

if __name__ == "__main__":
    app.run(debug=True)