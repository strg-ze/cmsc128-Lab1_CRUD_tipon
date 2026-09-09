# Agenda — CMSC128 Lab Activity 1 (CRUD)

**Agenda** is a simple, functional to-do list web app built with Flask and SQLite, featuring a Dashboard view, a Tasks management page, task editing/deletion with undo, and a built-in calendar view.

## Tech Stack

- **Frontend:** HTML, CSS
- **Templating:** Jinja2 (Flask's built-in templating engine)
- **Backend:** Flask (Python)
- **Database:** SQLite

### Why this stack

Flask + SQLite was chosen to emphasize clarity and foundational understanding in web application development. Flask’s lightweight design exposes the essential mechanics of routing, request handling, and response generation without the overhead of a larger framework. SQLite complements this by offering a self‑contained, file‑based database that requires no separate server process, making data interactions transparent and easy to inspect.

This combination provides a complete yet minimal stack: the frontend communicates with Flask, Flask processes and passes data to SQLite, and results are returned directly. By working without heavy abstractions, the project highlights the direct relationship between the application, its database, and the user interface. This approach is particularly well‑suited for a simple to‑do list app, where the data model is straightforward, the scale is modest, and the focus is on mastering CRUD operations and data flow.
### About Jinja2

Jinja2 is the templating engine Flask uses to embed Python-driven logic directly into HTML files. It's what allows `{{ }}` (print a value) and `{% %}` (control logic — loops, conditionals, template inheritance) to work inside `.html` templates. In this project, Jinja2 is used for:

- **Template inheritance** (`{% extends "base.html" %}`, `{% block content %}`) — so `dashboard.html` and `tasks.html` share one common page shell instead of duplicating the `<nav>` and `<head>` on every page.
- **Includes** (`{% include "partials/nav.html" %}`) — reusing the nav bar component across pages.
- **Loops** (`{% for task in tasks %}...{% endfor %}`) — rendering each row returned from a database query as an `<li>`.
- **Conditionals** (`{% if task['completed'] %}checked{% endif %}`) — conditionally applying attributes/styling based on task data.
- **Variable printing** (`{{ task['name'] }}`) — inserting database values into the rendered HTML.

## How to Run Locally

1. **Clone the repository**
    
    ```bash
    git clone https://github.com/strg-ze/cmsc128-Lab1_CRUD_tipon.git
    cd <your-repo-folder>
    ```
    
2. **Set up a virtual environment (recommended)**
    
    ```bash
    python -m venv venv
    venv\Scripts\activate      # Windows
    source venv/bin/activate   # macOS/Linux
    ```
    
3. **Install dependencies**
    
    ```bash
    pip install -r requirements.txt
    ```
    
4. **Initialize the database**
    
    ```bash
    python init_db.py
    ```
    
    This creates `database.db` using the schema defined in `schema.sql`.
    
5. **Run the app**
    
    ```bash
    python app.py
    ```
    
6. **Open in browser** Visit `http://localhost:5000`
    

## CRUD Operations (Flask Routes)

| Operation  | Method | Route                  | Description                                          |
| ---------- | ------ | ---------------------- | ---------------------------------------------------- |
| **Create** | POST   | `/tasks`               | Inserts a new task from the Add Task form            |
| **Read**   | GET    | `/`                    | Dashboard: today's tasks + calendar + upcoming tasks |
| **Read**   | GET    | `/tasks`               | Full visible task list                               |
| **Read**   | GET    | `/tasks/edit/<id>`     | Fetches one task, pre-fills the edit form            |
| **Update** | POST   | `/tasks/update/<id>`   | Saves edited task fields                             |
| **Update** | POST   | `/tasks/complete/<id>` | Toggles a task's completed status                    |
| **Delete** | POST   | `/tasks/delete/<id>`   | Soft-deletes a task (`is_visible = 0`)               |
| **Undo**   | POST   | `/tasks/restore/<id>`  | Undo — restores a soft-deleted task                  |

## Features

### Minimum Requirements

- To-do list interface (Dashboard + Tasks page)
- Add Task — title, description, due date, time, priority, tags, category
- Edit Task — pre-filled form, updates existing record
- Delete Task — confirmation dialog before deleting
- Mark Task as Done — checkbox toggle with strikethrough styling
- Data Persistence — SQLite database, survives app restarts

### Expanded Requirements (2 of 3 implemented)

1. **Undo on Delete** — after deleting, a toast notification appears with an Undo button; clicking it restores the task via the soft-delete flag.
2. **Calendar View** — the Dashboard includes a calendar grid showing the current month, with a dot marking any day that has tasks due. Clicking a day filters the Upcoming panel to show that day's tasks instead.

## Screenshots

![dashboard](/screenshots/image-1.png)
![tasks](/screenshots/image-2.png)
