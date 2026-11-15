from flask import Blueprint, request, redirect, url_for, session, flash

from init_db import get_db_connection
from routes.auth.decorators import login_required
from routes.auth.validators import check_email
from routes.lists.service import (
    clean_name, get_own_category_or_404, get_group_list_or_404,
)

bp = Blueprint("lists", __name__)

#individual page
@bp.route("/pages/new", methods=["POST"])
@login_required
def create_page():
    user_id = session["user_id"]
    name, error = clean_name(request.form.get("name"))
    conn = get_db_connection()
    try:
        if not error and conn.execute(
            "SELECT 1 FROM categories WHERE user_id = %s AND name = %s", (user_id, name)
        ).fetchone():
            error = "You already have a page with that name."
        if error:
            flash(error, "error")
            return redirect(url_for("tasks", mode="individual"))

        new_id = conn.execute(
            "INSERT INTO categories (user_id, name) VALUES (%s, %s) RETURNING id",
            (user_id, name),
        ).fetchone()["id"]
        conn.commit()
        flash(f'Page "{name}" created.', "success")
        return redirect(url_for("tasks", mode="individual", page=new_id))
    finally:
        conn.close()


@bp.route("/pages/<int:category_id>/rename", methods=["POST"])
@login_required
def rename_page(category_id):
    user_id = session["user_id"]
    name, error = clean_name(request.form.get("name"))
    conn = get_db_connection()
    try:
        get_own_category_or_404(conn, category_id, user_id)     # ownership check
        if not error and conn.execute(
            "SELECT 1 FROM categories WHERE user_id = %s AND name = %s AND id != %s",
            (user_id, name, category_id),
        ).fetchone():
            error = "You already have a page with that name."
        if error:
            flash(error, "error")
        else:
            conn.execute("UPDATE categories SET name = %s WHERE id = %s", (name, category_id))
            conn.commit()
            flash("Page renamed.", "success")
        return redirect(url_for("tasks", mode="individual", page=category_id))
    finally:
        conn.close()


@bp.route("/pages/<int:category_id>/delete", methods=["POST"])
@login_required
def delete_page(category_id):
    conn = get_db_connection()
    try:
        get_own_category_or_404(conn, category_id, session["user_id"])
        conn.execute("DELETE FROM categories WHERE id = %s", (category_id,))
        conn.commit()
        flash("Page deleted. Its tasks are now uncategorized.", "success")
        return redirect(url_for("tasks", mode="individual"))
    finally:
        conn.close()


# group list
@bp.route("/lists/new", methods=["POST"])
@login_required
def create_list():
    user_id = session["user_id"]
    name, error = clean_name(request.form.get("name"))
    if error:
        flash(error, "error")
        return redirect(url_for("tasks", mode="group"))

    conn = get_db_connection()
    try:
        list_id = conn.execute(
            "INSERT INTO lists (name, owner_id, is_personal) VALUES (%s, %s, 0) RETURNING id",
            (name, user_id),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO list_members (list_id, user_id) VALUES (%s, %s)", (list_id, user_id)
        )
        conn.commit()
        flash(f'List "{name}" created.', "success")
        return redirect(url_for("tasks", mode="group", list=list_id))
    finally:
        conn.close()


@bp.route("/lists/<int:list_id>/rename", methods=["POST"])
@login_required
def rename_list(list_id):
    name, error = clean_name(request.form.get("name"))
    conn = get_db_connection()
    try:
        get_group_list_or_404(conn, list_id, session["user_id"], owner_only=True)
        if error:
            flash(error, "error")
        else:
            conn.execute("UPDATE lists SET name = %s WHERE id = %s", (name, list_id))
            conn.commit()
            flash("List renamed.", "success")
        return redirect(url_for("tasks", mode="group", list=list_id))
    finally:
        conn.close()


@bp.route("/lists/<int:list_id>/members/add", methods=["POST"])
@login_required
def add_member(list_id):
    email = request.form.get("email", "").strip().lower()
    conn = get_db_connection()
    try:
        get_group_list_or_404(conn, list_id, session["user_id"], owner_only=True)

        error = check_email(email)
        target = None
        if not error:
            target = conn.execute(
                "SELECT id, display_name FROM users WHERE email = %s", (email,)
            ).fetchone()
            if target is None:
                error = "No account found with that email."
            elif conn.execute(
                "SELECT 1 FROM list_members WHERE list_id = %s AND user_id = %s",
                (list_id, target["id"]),
            ).fetchone():
                error = f"{target['display_name']} is already a member."

        if error:
            flash(error, "error")
        else:
            conn.execute(
                "INSERT INTO list_members (list_id, user_id) VALUES (%s, %s)",
                (list_id, target["id"]),
            )
            conn.commit()
            flash(f"{target['display_name']} was added to the list.", "success")
        return redirect(url_for("tasks", mode="group", list=list_id))
    finally:
        conn.close()


@bp.route("/lists/<int:list_id>/members/<int:member_id>/remove", methods=["POST"])
@login_required
def remove_member(list_id, member_id):
    conn = get_db_connection()
    try:
        lst = get_group_list_or_404(conn, list_id, session["user_id"], owner_only=True)
        if member_id == lst["owner_id"]:
            flash("The owner can't be removed. Delete the list instead.", "error")
        else:
            conn.execute(
                "DELETE FROM list_members WHERE list_id = %s AND user_id = %s",
                (list_id, member_id),
            )
            conn.commit()
            flash("Member removed.", "success")
        return redirect(url_for("tasks", mode="group", list=list_id))
    finally:
        conn.close()


@bp.route("/lists/<int:list_id>/leave", methods=["POST"])
@login_required
def leave_list(list_id):
    user_id = session["user_id"]
    conn = get_db_connection()
    try:
        lst = get_group_list_or_404(conn, list_id, user_id)       # any member
        if lst["owner_id"] == user_id:
            flash("Owners can't leave their own list. Delete it instead.", "error")
            return redirect(url_for("tasks", mode="group", list=list_id))
        conn.execute(
            "DELETE FROM list_members WHERE list_id = %s AND user_id = %s", (list_id, user_id)
        )
        conn.commit()
        flash("You left the list.", "success")
        return redirect(url_for("tasks", mode="group"))
    finally:
        conn.close()


@bp.route("/lists/<int:list_id>/delete", methods=["POST"])
@login_required
def delete_list(list_id):
    conn = get_db_connection()
    try:
        get_group_list_or_404(conn, list_id, session["user_id"], owner_only=True)
        conn.execute("DELETE FROM lists WHERE id = %s", (list_id,))
        conn.commit()
        flash("List deleted.", "success")
        return redirect(url_for("tasks", mode="group"))
    finally:
        conn.close()