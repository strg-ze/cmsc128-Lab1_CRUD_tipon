DEFAULT_CATEGORIES = ("School", "Personal", "Work")

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