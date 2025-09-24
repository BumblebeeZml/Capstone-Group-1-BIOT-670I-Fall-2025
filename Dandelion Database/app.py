from flask import Flask, session, redirect, url_for, render_template
from login_register_bp import login_register_bp
from files_bp import files_bp
from db import ensure_db

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for sessions

# Ensure DB exists
ensure_db()

# Register blueprints
app.register_blueprint(login_register_bp, url_prefix="/login_register")
app.register_blueprint(files_bp, url_prefix="/files")

@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for("files.index"))
    return render_template("Home.html")  # Create this template

if __name__ == "__main__":
    app.run(debug=True)
