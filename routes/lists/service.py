from flask import abort

DEFAULT_CATEGORIES = ("School", "Personal", "Work")
NAME_MAX = 30

# setup
def create_default_workplace(conn, user_id):
    cur = conn.execute(
        "INSERT INTO lists (name, owner_id, is_personal) VALUES ('My Tasks',?,1)",
        (user_id,)
    )

    conn.execute(
        "INSERT INTO list_members (list_id, user_id) VALUES (?, ?)",
        (cur.lastrowid, user_id),
    )

    for name in DEFAULT_CATEGORIES:
        conn.execute(
            "INSERT INTO categories (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )

# validation
def clean_name(raw):
    name = (raw or "").strip()
    if not name:
        return None, "Please enter a name."
    if len(name) > NAME_MAX:
        return None, f"Name cannot exceed {NAME_MAX} characters."
    return name, None

# personal page (categories)

def get_personal_list_id(conn,user_id):
    row = conn.execute(
        'SELECT id FROM lists WHERE owner_id = ? AND is_personal = 1',
        (user_id,)
    ).fetchone()
    return row["id"]

def get_categories(conn, user_id):
    return conn.execute(
        'SELECT id, name FROM categories WHERE user_id = ? ORDER BY name',
        (user_id,)
    ).fetchall()

def get_own_category_or_404(conn, category_id, user_id):
    row = conn.execute(
        'SELECT id, name FROM categories WHERE id = ? AND user_id = ?',(category_id,user_id,)
        ).fetchone()
    if row is None:
        abort(404)
    return row

def parse_category_id(conn,user_id,raw):
    if not raw:
        return None
    if not raw.isdigit():
        abort(404)
    get_own_category_or_404(conn, int(raw), user_id)
    return int(raw)

#group lists
def get_group_lists(conn, user_id):
    return conn.execute(
        """SELECT l.id, l.name, l.owner_id 
           FROM lists l JOIN list_members m ON m.list_id = l.id
           WHERE m.user_id = ? AND l.is_personal = 0
           ORDER BY l.name""",
           (user_id,),
        ).fetchall()

def get_group_list_or_404(conn, list_id, user_id, owner_only=False):
    row = conn.execute(
        """SELECT l.id, l.name, l.owner_id 
           FROM lists l JOIN list_members m ON m.list_id = l.id
           WHERE l.id = ? AND m.user_id = ? AND l.is_personal = 0""",
           (list_id, user_id),
        ).fetchone()
    if row is None:
        abort(404)
    if owner_only and row["owner_id"] != user_id:
        abort(403)
    return row

def get_members(conn, list_id):
    return conn.execute(
        """SELECT u.id, u.display_name AS name,
            CASE WHEN u.id = l.owner_id THEN 'owner' ELSE 'member' END AS role
            FROM list_members m
            JOIN users u ON u.id = m.user_id
            JOIN lists l ON l.id = m.list_id
            WHERE m.list_id = ?
            ORDER BY (u.id = l.owner_id) DESC, u.display_name""",
        (list_id,),
    ).fetchall()

#tasks
def get_task_for_user (conn, task_id, user_id):
    return conn.execute(
        """SELECT t.*, l.is_personal
           FROM tasks t
           JOIN lists l ON l.id = t.list_id
           JOIN list_members m ON m.list_id = l.id
           WHERE t.id = ? AND m.user_id = ?""",
           (task_id, user_id)
    ).fetchone()

def get_tasks_for_view(conn, user_id, mode, selected):
    if mode == "group":
        query = """SELECT t.*, l.name AS list_name, u.display_name AS added_by
                   FROM tasks t
                   JOIN lists l ON l.id = t.list_id AND l.is_personal = 0
                   JOIN list_members m ON m.list_id = l.id AND m.user_id = ?
                   LEFT JOIN users u ON u.id = t.user_id
                   WHERE t.is_visible = 1"""
        params = [user_id]
        if selected:
            query += " AND l.id = ?"
            params.append(int(selected))
    else:
        query = """SELECT t.*, c.name AS category
                    FROM tasks t
                    JOIN lists l ON l.id = t.list_id AND l.is_personal = 1
                    JOIN list_members m ON m.list_id = l.id AND m.user_id = ?
                    LEFT JOIN categories c ON c.id = t.category_id
                    WHERE t.is_visible = 1"""
        params = [user_id]
        if selected:
            query += " AND t.category_id = ?"
            params.append(int(selected))

    query += " ORDER BY t.due_date, t.time"
    return conn.execute(query, params).fetchall()