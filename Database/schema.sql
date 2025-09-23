-- schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS files (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filename     TEXT    NOT NULL,
    mime_type    TEXT,
    size_bytes   INTEGER,
    storage_path TEXT    NOT NULL,
    comment      TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_files_filename ON files (filename);
