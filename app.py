from flask import Flask, render_template, request, redirect
import sqlite3
import hashlib

app = Flask(__name__)
DB_PATH = "Tables.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def md5_hash(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()    

#Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = md5_hash(password)

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            return f"Welcome, {username}!"
        else:
            return "Invalid credentials, try again."

    return render_template('loginPage.html')

#Register as new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = md5_hash(password)

        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return "Username already exists. Please choose a different username."

    return render_template('registerUser.html')

#Home Page
@app.route('/')
def home():
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)