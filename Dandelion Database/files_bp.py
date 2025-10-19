from flask import Blueprint, render_template, request, redirect, url_for, session, abort, send_file, make_response
from functools import wraps
from werkzeug.utils import secure_filename
from pathlib import Path
from mimetypes import guess_type
from db import get_conn_cm, ensure_db

UPLOAD_DIR = Path(r"C:\Users\amand\Downloads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

files_bp = Blueprint("files", __name__, template_folder="templates")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login_register_bp.login"))
        return f(*args, **kwargs)
    return decorated_function

def _unique_path(directory: Path, filename: str) -> Path:
    safe = secure_filename(filename or "")
    if not safe:
        safe = "upload"
    target = directory / safe
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    i = 1
    while True:
        candidate = directory / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1

def _render_index(error=None, qs=None):
    """Render the files page with optional search query."""
    with get_conn_cm() as conn:
        # Get column names from the table
        col_info = conn.execute("PRAGMA table_info(files);").fetchall()
        columns = [c["name"] for c in col_info]

        # Fetch all rows
        rows = conn.execute("SELECT * FROM files ORDER BY created_at DESC, id DESC;").fetchall()

        # Filter by search query if provided
        if qs:
            qs_lower = qs.lower()
            rows = [r for r in rows if qs_lower in r["filename"].lower() or (r["comment"] and qs_lower in r["comment"].lower())]

    resp = make_response(render_template(
        "index.html",
        columns=columns,
        rows=rows,
        error=error,
        upload_dir=str(UPLOAD_DIR),
    ))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

def _get_file_row(file_id: int):
    with get_conn_cm() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?;", (file_id,)).fetchone()
    return row

@files_bp.get("/")
@login_required
def index():
     return _render_index()

@files_bp.post("/upload")
@login_required
def upload_file():
     file = request.files.get("file")
     comment = (request.form.get("comment") or "").strip() or None
     if not file or not file.filename:
         return _render_index(error="Please choose a file to upload."), 400

     dest = _unique_path(UPLOAD_DIR, file.filename)
     try:
         file.save(str(dest))
     except Exception as e:
         return _render_index(error=f"Failed to save file: {e}"), 500

     filename = dest.name
     size_bytes = dest.stat().st_size
     mime_type = file.mimetype or guess_type(str(dest))[0]

     with get_conn_cm() as conn:
         conn.execute(
             """
             INSERT INTO files (filename, mime_type, size_bytes, storage_path, comment)
             VALUES (?, ?, ?, ?, ?);
             """,
                (filename, mime_type, size_bytes, str(dest), comment),
            )

     return redirect(url_for("files.index"))

@files_bp.get("/files/<int:file_id>/download")
@login_required
def download_file(file_id):
    row = _get_file_row(file_id)
    if not row:
        abort(404)
    p = Path(row["storage_path"])
    if not p.exists():
        abort(404)
    return send_file(p, as_attachment=True, download_name=row["filename"])

@files_bp.post("/files/<int:file_id>/delete")
@login_required
def delete_file(file_id):
    row = _get_file_row(file_id)
    if row:
        p = Path(row["storage_path"])
        try:
            if p.exists():
                p.unlink()
        except Exception:
             pass
        with get_conn_cm() as conn:
             conn.execute("DELETE FROM files WHERE id = ?;", (file_id,))
    return redirect(url_for("files.index"))