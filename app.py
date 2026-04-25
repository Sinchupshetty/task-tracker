from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "tasktracker_secret_key_2024"

DB_PATH = "tasks.db"

# ─────────────────────────────────────────────
# Database setup
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        # Seed a demo user (password: demo123)
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("demo", "demo123"))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already exists

init_db()

# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# Auth routes
# ─────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("tasks"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Please fill in all fields.", "error")
            return render_template("login.html")
        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, password)
            ).fetchone()
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("tasks"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Please fill in all fields.", "error")
            return render_template("register.html")
        if len(password) < 4:
            flash("Password must be at least 4 characters.", "error")
            return render_template("register.html")
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already taken.", "error")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("login"))

# ─────────────────────────────────────────────
# Task CRUD routes
# ─────────────────────────────────────────────
@app.route("/tasks")
@login_required
def tasks():
    filter_by = request.args.get("filter", "all")
    priority = request.args.get("priority", "all")
    sort_by = request.args.get("sort", "created_at")

    query = "SELECT * FROM tasks WHERE user_id = ?"
    params = [session["user_id"]]

    if filter_by == "active":
        query += " AND completed = 0"
    elif filter_by == "done":
        query += " AND completed = 1"

    if priority != "all":
        query += " AND priority = ?"
        params.append(priority)

    order_map = {
        "created_at": "created_at DESC",
        "due_date": "CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END, due_date ASC",
        "priority": "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END"
    }
    query += f" ORDER BY {order_map.get(sort_by, 'created_at DESC')}"

    with get_db() as conn:
        all_tasks = conn.execute(query, params).fetchall()
        counts = conn.execute(
            "SELECT completed, COUNT(*) as cnt FROM tasks WHERE user_id = ? GROUP BY completed",
            [session["user_id"]]
        ).fetchall()

    total = sum(r["cnt"] for r in counts)
    done = next((r["cnt"] for r in counts if r["completed"] == 1), 0)

    return render_template("tasks.html",
        tasks=all_tasks,
        filter_by=filter_by,
        priority=priority,
        sort_by=sort_by,
        total=total,
        done=done,
        today=datetime.today().strftime("%Y-%m-%d")
    )

@app.route("/tasks/add", methods=["POST"])
@login_required
def add_task():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority", "medium")
    due_date = request.form.get("due_date", "").strip()

    if not title:
        flash("Task title cannot be empty.", "error")
        return redirect(url_for("tasks"))

    if priority not in ("high", "medium", "low"):
        priority = "medium"

    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (user_id, title, description, priority, due_date) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], title, description, priority, due_date or None)
        )
        conn.commit()
    flash("Task added!", "success")
    return redirect(url_for("tasks"))

@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    with get_db() as conn:
        task = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"])
        ).fetchone()

    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("tasks"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "medium")
        due_date = request.form.get("due_date", "").strip()

        if not title:
            flash("Task title cannot be empty.", "error")
            return render_template("edit_task.html", task=task)

        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET title=?, description=?, priority=?, due_date=? WHERE id=? AND user_id=?",
                (title, description, priority, due_date or None, task_id, session["user_id"])
            )
            conn.commit()
        flash("Task updated!", "success")
        return redirect(url_for("tasks"))

    return render_template("edit_task.html", task=task)

@app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    with get_db() as conn:
        task = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"])
        ).fetchone()
        if task:
            conn.execute(
                "UPDATE tasks SET completed = ? WHERE id = ? AND user_id = ?",
                (0 if task["completed"] else 1, task_id, session["user_id"])
            )
            conn.commit()
    return redirect(url_for("tasks",
        filter=request.args.get("filter","all"),
        priority=request.args.get("priority","all"),
        sort=request.args.get("sort","created_at")
    ))

@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"])
        )
        conn.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("tasks"))

if __name__ == "__main__":
    app.run(debug=True)
