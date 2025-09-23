
from pathlib import Path
from mimetypes import guess_type

from flask import (
    Flask, render_template, request, redirect,
    url_for, make_response, send_file, abort
)
from werkzeug.utils import secure_filename

from db import ensure_db, get_conn

# Upload destination on your PC
UPLOAD_DIR = Path(r"C:\Users\lacky\PyCharmMiscProject\Database\Uploads")

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
    with get_conn() as conn:
        col_info = conn.execute("PRAGMA table_info(files);").fetchall()
        columns = [c["name"] for c in col_info]
        rows = conn.execute(
            "SELECT * FROM files ORDER BY created_at DESC, id DESC;"
        ).fetchall()

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
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?;", (file_id,)).fetchone()
    return row

def create_app():
    app = Flask(__name__, template_folder="templates")
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    ensure_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @app.after_request
    def add_no_cache_headers(resp):
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.get("/")
    def index():
        return _render_index()

    @app.post("/upload")
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

        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO files (filename, mime_type, size_bytes, storage_path, comment)
                VALUES (?, ?, ?, ?, ?);
                """,
                (filename, mime_type, size_bytes, str(dest), comment),
            )

        return redirect(url_for("index"))

    @app.get("/files/<int:file_id>/download")
    def download_file(file_id):
        row = _get_file_row(file_id)
        if not row:
            abort(404)
        p = Path(row["storage_path"])
        if not p.exists():
            abort(404)
        return send_file(p, as_attachment=True, download_name=row["filename"])

    @app.post("/files/<int:file_id>/delete")
    def delete_file(file_id):
        row = _get_file_row(file_id)
        if row:
            p = Path(row["storage_path"])
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
            with get_conn() as conn:
                conn.execute("DELETE FROM files WHERE id = ?;", (file_id,))
        return redirect(url_for("index"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)  # http://127.0.0.1:5000/
