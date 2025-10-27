from flask import Blueprint, render_template, request, redirect, url_for, session, abort, send_file, make_response
from functools import wraps
from werkzeug.utils import secure_filename
from pathlib import Path
from mimetypes import guess_type
from db import get_conn_cm
from metadata_utils import extract_metadata
import sqlite3


# Uploads directory lives alongside this file (project-root/Uploads)
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "Uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

files_bp = Blueprint("files", __name__, template_folder="templates")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login_register_bp.login"))
        return f(*args, **kwargs)
    return decorated_function

def _get_file_row(file_id: int):
    """Return the row from files table or None if not found."""
    from db import get_conn_cm
    with get_conn_cm() as conn:
        return conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()

def _resolve_disk_path(row):
    """
    Try to figure out where the file lives on disk, being tolerant of schema differences.
    Prefers absolute stored paths if present; falls back to Uploads/<filename>.
    """
    # Try common column names people use for stored paths
    candidates = ["stored_path", "file_path", "filepath", "path"]
    for key in candidates:
        if key in row.keys() and row[key]:
            p = Path(row[key])
            return p if p.is_absolute() else (UPLOAD_DIR / p)

    # Fallback to filename in Uploads
    name = row["filename"] if "filename" in row.keys() else None
    return (UPLOAD_DIR / name) if name else None

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

def _render_index(error=None):
    with get_conn_cm() as conn:
        col_info = conn.execute("PRAGMA table_info(files);").fetchall()
        columns = [c["name"] for c in col_info]
        raw_rows = conn.execute("SELECT * FROM files ORDER BY created_at DESC, id DESC;").fetchall()

        enriched_rows = []
        for r in raw_rows:
            file_id = r["id"]
            metadata_rows = conn.execute(
                "SELECT meta_key, meta_value FROM metadata WHERE file_id = ?",
                (file_id,)
            ).fetchall()

            r = dict(r)
            r["metadata"] = {m["meta_key"]: m["meta_value"] for m in metadata_rows}
            enriched_rows.append(r)

    resp = make_response(render_template(
        "index.html",
        columns=columns,
        rows=enriched_rows,
        error=error,
        upload_dir=str(UPLOAD_DIR),
    ))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

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

    metadata = extract_metadata(str(dest))
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

        file_id = conn.execute("SELECT last_insert_rowid();").fetchone()[0]

        for key, value in metadata.items():
            conn.execute(
                """
                INSERT INTO metadata (file_id, meta_key, meta_value)
                VALUES (?, ?, ?);
                """,
                (file_id, key, value),
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

@files_bp.route("/delete/<int:file_id>", methods=["POST", "GET"])
@login_required
def delete_file(file_id: int):
    """
    Delete a file record (and its metadata if present) and remove the file from disk.
    Accepts GET for compatibility with existing templates, but prefer POST in forms.
    """
    row = _get_file_row(file_id)
    if row is None:
        # File ID doesn't exist
        abort(404, description="File not found")

    disk_path = _resolve_disk_path(row)

    # 1) Remove DB rows first (so UI stops showing the file even if disk removal fails)
    from db import get_conn_cm
    with get_conn_cm() as conn:
        # Best-effort: some schemas have a metadata table linked by file_id; ignore if it doesn't exist
        try:
            conn.execute("DELETE FROM metadata WHERE file_id = ?", (file_id,))
        except sqlite3.OperationalError:
            # metadata table (or column) may not exist; that's okay
            pass

        # Remove the file record itself
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))

    # 2) Then try to remove the actual file from disk (won't raise if missing)
    try:
        if disk_path and disk_path.exists():
            disk_path.unlink()
    except Exception:
        # Don't crash the request just because the file couldn't be deleted on disk
        # (you can log this if you have logging configured)
        pass

    # Back to the index (or wherever you list files)
    return redirect(url_for("files.index"))

### search function added by DM
@files_bp.post("/search")
@login_required
def search():
    search_query = request.form['query']
    with get_conn_cm() as conn:
        col_info = conn.execute("PRAGMA table_info(files);").fetchall()
        columns = [c["name"] for c in col_info]
        rows = conn.execute(
             "SELECT * FROM files WHERE filename LIKE ?", ('%' + search_query + '%',)
        ).fetchall()

    resp = make_response(render_template(
        "search.html",
        columns=columns,
        rows=rows,
        upload_dir=str(UPLOAD_DIR),  # optional to display where files go
    ))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp