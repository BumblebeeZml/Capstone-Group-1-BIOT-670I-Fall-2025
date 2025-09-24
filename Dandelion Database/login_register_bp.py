from flask import Blueprint, render_template, request, redirect, url_for, make_response, session
import sqlite3
import hashlib
from db import get_conn_cm

# Define the blueprint
login_register_bp = Blueprint("login_register_bp", __name__, template_folder="templates")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def md5_hash(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()

# Login Page
@login_register_bp.route('/login', methods=['GET', 'POST'])
def login():
    if "user_id" in session:
        return redirect(url_for("files.index"))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = md5_hash(password)

        with get_conn_cm() as conn:
           user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
           conn.close()

        if user and user['password_md5'] == hashed_password:
            session['user_id'] = user['id']
            session['username'] = user['username']

            resp = redirect(url_for("files.index"))

            # Only set cookie if "Remember me" is checked
            if 'remember_me' in request.form:
                resp.set_cookie("remember_username", user['username'], max_age=60*60*24*30)
            else:
                # Clear cookie if it exists
                resp.set_cookie("remember_username", '', expires=0)

            return resp
        else:
            return "Invalid credentials, try again."

    # Prefill username if cookie exists
    remembered_username = request.cookies.get("remember_username")
    return render_template('loginPage.html', remembered_username=remembered_username)

# Register as new user
@login_register_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = md5_hash(password)

        try:
          with get_conn_cm() as conn:
            conn.execute("INSERT INTO users (username, password_md5) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect('/login_register/login')
        except sqlite3.IntegrityError:
            return "Username already exists. Please choose a different username."

    return render_template('registerUser.html')

@login_register_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_register_bp.login"))