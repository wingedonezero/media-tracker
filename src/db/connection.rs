use rusqlite::Connection;

pub fn init_db(data_dir: &std::path::Path) -> Result<Connection, Box<dyn std::error::Error>> {
    std::fs::create_dir_all(data_dir)?;
    let db_path = data_dir.join("media_tracker.db");
    let conn = Connection::open(db_path)?;
    conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;")?;
    run_migrations(&conn)?;
    Ok(conn)
}

fn run_migrations(conn: &Connection) -> Result<(), rusqlite::Error> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            native_title TEXT,
            romaji_title TEXT,
            year INTEGER,
            media_type TEXT NOT NULL,
            status TEXT NOT NULL,
            quality_type TEXT,
            source TEXT,
            notes TEXT,
            tmdb_id INTEGER,
            anilist_id INTEGER,
            poster_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_media_type_status ON media_items(media_type, status);
        CREATE INDEX IF NOT EXISTS idx_title ON media_items(title);",
    )?;
    Ok(())
}
