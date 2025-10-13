# app.py
from flask import Flask, session, redirect, url_for, render_template
from login_register_bp import login_register_bp
from files_bp import files_bp
from db import ensure_db

# Use a single global templates folder at project_root/templates
app = Flask(__name__, template_folder="templates")

# TODO: replace with a strong, secret value in production (e.g., from env var)
app.secret_key = "supersecretkey"

# Make sure the database and tables exist before serving requests
ensure_db()

# Register blueprints
# Auth pages at /login, /register, and /logout
app.register_blueprint(login_register_bp, url_prefix="")

# Files UI under /files
app.register_blueprint(files_bp, url_prefix="/files")

# Home route:
# - If logged in, send to the files table
# - If not, render your custom Home.html (landing page with links)
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("files.index"))
    return render_template("Home.html")

# Optional: small no-cache shim for dynamic pages (helps avoid stale redirects)
@app.after_request
def add_no_cache_headers(resp):
    resp.headers.setdefault("Cache-Control", "no-store")
    return resp

if __name__ == "__main__":
    # Choose exactly one interface to bind to:

    # 1) Local-only (recommended for development on your machine)
    app.config["SERVER_NAME"] = "127.0.0.1:5000"  # helps if you ever build external URLs
    app.run(debug=True, host="127.0.0.1", port=5000)

    # 2) OR LAN-only (others on your network can reach you at http://10.0.0.125:5000)
    # app.config["SERVER_NAME"] = "10.0.0.125:5000"
    # app.run(debug=True, host="10.0.0.125", port=5000)

    # Do NOT use host="0.0.0.0" if you want a single address.
