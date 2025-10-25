PRAGMA foreign_keys = ON;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_md5 TEXT NOT NULL
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER,
    filename     TEXT    NOT NULL,
    mime_type    TEXT,
    size_bytes   INTEGER,
    storage_path TEXT    NOT NULL,
    comment      TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS metadata (
    file_id    INTEGER      NOT NULL
                            REFERENCES files (id),
    meta_key   VARCHAR (50) NOT NULL,
    meta_value TEXT,
    PRIMARY KEY (
        file_id,
        meta_key
    )
);

-- Index on filenames
CREATE INDEX IF NOT EXISTS idx_files_filename ON files (filename);
