from flask import Blueprint, render_template, request, redirect, url_for, make_response, session
import hashlib
import sqlite3
from db import get_conn_cm

login_register_bp = Blueprint("login_register_bp", __name__)

def md5_hash(password: str) -> str:
    # NOTE: For production, use werkzeug.security.generate_password_hash / check_password_hash
    return hashlib.md5(password.encode()).hexdigest()

@login_register_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember_me = bool(request.form.get("remember_me"))

        if not username or not password:
            # Pass remembered_username back so the input can be prefilled
            return render_template("loginPage.html", remembered_username=username, error="Username and password are required.")

        hashed = md5_hash(password)
        with get_conn_cm() as conn:
            row = conn.execute(
                "SELECT id, username FROM users WHERE username = ? AND password_md5 = ?;",
                (username, hashed),
            ).fetchone()

        if not row:
            return render_template("loginPage.html", remembered_username=username, error="Invalid credentials.")

        # Auth OK
        session["user_id"] = row["id"]
        session["username"] = row["username"]

        resp = make_response(redirect(url_for("files.index")))
        # handle "Remember me" cookie for username prefill on future visits
        if remember_me:
            resp.set_cookie("remembered_username", username, max_age=60 * 60 * 24 * 30, httponly=False, samesite="Lax")
        else:
            resp.delete_cookie("remembered_username")
        resp.headers["Cache-Control"] = "no-store"
        return resp

    # GET: prefill from cookie if present
    remembered_username = request.cookies.get("remembered_username", "")
    return render_template("loginPage.html", remembered_username=remembered_username)

@login_register_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template("registerUser.html", error="Username and password are required.")

        hashed = md5_hash(password)
        try:
            with get_conn_cm() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_md5) VALUES (?, ?);",
                    (username, hashed),
                )
        except sqlite3.IntegrityError:
            return render_template("registerUser.html", error="Username already exists.")

        return redirect(url_for("login_register_bp.login"))

    return render_template("registerUser.html")

@login_register_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_register_bp.login"))
