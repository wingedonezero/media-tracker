use crate::models::{BatchAddResult, MediaItem};
use rusqlite::{params, Connection};

fn row_to_item(row: &rusqlite::Row) -> rusqlite::Result<MediaItem> {
    Ok(MediaItem {
        id: Some(row.get(0)?),
        title: row.get(1)?,
        native_title: row.get(2)?,
        romaji_title: row.get(3)?,
        year: row.get(4)?,
        media_type: row.get(5)?,
        status: row.get(6)?,
        quality_type: row.get(7)?,
        source: row.get(8)?,
        notes: row.get(9)?,
        tmdb_id: row.get(10)?,
        anilist_id: row.get(11)?,
        poster_url: row.get(12)?,
        created_at: row.get(13)?,
        updated_at: row.get(14)?,
    })
}

pub fn get_items(
    conn: &Connection,
    media_type: Option<&str>,
    status: Option<&str>,
) -> Result<Vec<MediaItem>, rusqlite::Error> {
    get_items_sorted(conn, media_type, status, "title", "ASC")
}

pub fn get_items_sorted(
    conn: &Connection,
    media_type: Option<&str>,
    status: Option<&str>,
    sort_field: &str,
    sort_dir: &str,
) -> Result<Vec<MediaItem>, rusqlite::Error> {
    let mut sql = String::from(
        "SELECT id, title, native_title, romaji_title, year, media_type, status,
                quality_type, source, notes, tmdb_id, anilist_id, poster_url,
                created_at, updated_at FROM media_items WHERE 1=1",
    );
    let mut param_values: Vec<Box<dyn rusqlite::types::ToSql>> = Vec::new();

    if let Some(mt) = media_type {
        sql.push_str(" AND media_type = ?");
        param_values.push(Box::new(mt.to_string()));
    }
    if let Some(s) = status {
        sql.push_str(" AND status = ?");
        param_values.push(Box::new(s.to_string()));
    }

    // Whitelist sort columns to prevent SQL injection
    let col = match sort_field {
        "year" => "year",
        "quality_type" => "quality_type",
        "source" => "source",
        _ => "title",
    };
    let dir = if sort_dir == "DESC" { "DESC" } else { "ASC" };
    sql.push_str(&format!(" ORDER BY {} {} NULLS LAST", col, dir));

    let params_refs: Vec<&dyn rusqlite::types::ToSql> =
        param_values.iter().map(|p| p.as_ref()).collect();
    let mut stmt = conn.prepare(&sql)?;
    let items = stmt
        .query_map(params_refs.as_slice(), |row| row_to_item(row))?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(items)
}

pub fn add_item(conn: &Connection, item: &MediaItem) -> Result<i64, rusqlite::Error> {
    conn.execute(
        "INSERT INTO media_items (title, native_title, romaji_title, year, media_type, status,
         quality_type, source, notes, tmdb_id, anilist_id, poster_url)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
        params![
            item.title,
            item.native_title,
            item.romaji_title,
            item.year,
            item.media_type,
            item.status,
            item.quality_type,
            item.source,
            item.notes,
            item.tmdb_id,
            item.anilist_id,
            item.poster_url,
        ],
    )?;
    Ok(conn.last_insert_rowid())
}

pub fn add_items_batch(
    conn: &Connection,
    items: &[MediaItem],
    skip_duplicates: bool,
) -> Result<BatchAddResult, rusqlite::Error> {
    let mut result = BatchAddResult {
        added: 0,
        skipped: 0,
        errors: 0,
        added_items: Vec::new(),
        skipped_items: Vec::new(),
        error_items: Vec::new(),
    };

    let tx = conn.unchecked_transaction()?;
    for item in items {
        if skip_duplicates && check_duplicate_by_id(&tx, item)? {
            result.skipped += 1;
            result.skipped_items.push(item.title.clone());
            continue;
        }

        match tx.execute(
            "INSERT INTO media_items (title, native_title, romaji_title, year, media_type, status,
             quality_type, source, notes, tmdb_id, anilist_id, poster_url)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
            params![
                item.title,
                item.native_title,
                item.romaji_title,
                item.year,
                item.media_type,
                item.status,
                item.quality_type,
                item.source,
                item.notes,
                item.tmdb_id,
                item.anilist_id,
                item.poster_url,
            ],
        ) {
            Ok(_) => {
                result.added += 1;
                result.added_items.push(item.title.clone());
            }
            Err(e) => {
                result.errors += 1;
                result
                    .error_items
                    .push(format!("{}: {}", item.title, e));
            }
        }
    }
    tx.commit()?;
    Ok(result)
}

pub fn update_item(conn: &Connection, item: &MediaItem) -> Result<(), rusqlite::Error> {
    conn.execute(
        "UPDATE media_items SET title=?1, native_title=?2, romaji_title=?3, year=?4,
         media_type=?5, status=?6, quality_type=?7, source=?8, notes=?9,
         tmdb_id=?10, anilist_id=?11, poster_url=?12, updated_at=CURRENT_TIMESTAMP
         WHERE id=?13",
        params![
            item.title,
            item.native_title,
            item.romaji_title,
            item.year,
            item.media_type,
            item.status,
            item.quality_type,
            item.source,
            item.notes,
            item.tmdb_id,
            item.anilist_id,
            item.poster_url,
            item.id,
        ],
    )?;
    Ok(())
}

pub fn delete_item(conn: &Connection, id: i64) -> Result<(), rusqlite::Error> {
    conn.execute("DELETE FROM media_items WHERE id = ?1", params![id])?;
    Ok(())
}

pub fn delete_items_batch(conn: &Connection, ids: &[i64]) -> Result<(), rusqlite::Error> {
    if ids.is_empty() {
        return Ok(());
    }
    let placeholders: Vec<String> = ids.iter().enumerate().map(|(i, _)| format!("?{}", i + 1)).collect();
    let sql = format!(
        "DELETE FROM media_items WHERE id IN ({})",
        placeholders.join(", ")
    );
    let params: Vec<Box<dyn rusqlite::types::ToSql>> =
        ids.iter().map(|id| Box::new(*id) as Box<dyn rusqlite::types::ToSql>).collect();
    let params_refs: Vec<&dyn rusqlite::types::ToSql> =
        params.iter().map(|p| p.as_ref()).collect();
    conn.execute(&sql, params_refs.as_slice())?;
    Ok(())
}

pub fn move_items(
    conn: &Connection,
    ids: &[i64],
    new_status: &str,
) -> Result<(), rusqlite::Error> {
    if ids.is_empty() {
        return Ok(());
    }
    let placeholders: Vec<String> = ids.iter().enumerate().map(|(i, _)| format!("?{}", i + 2)).collect();
    let sql = format!(
        "UPDATE media_items SET status = ?1, updated_at = CURRENT_TIMESTAMP WHERE id IN ({})",
        placeholders.join(", ")
    );
    let mut param_values: Vec<Box<dyn rusqlite::types::ToSql>> = Vec::new();
    param_values.push(Box::new(new_status.to_string()));
    for id in ids {
        param_values.push(Box::new(*id));
    }
    let params_refs: Vec<&dyn rusqlite::types::ToSql> =
        param_values.iter().map(|p| p.as_ref()).collect();
    conn.execute(&sql, params_refs.as_slice())?;
    Ok(())
}

pub fn search_items(
    conn: &Connection,
    term: &str,
    media_type: Option<&str>,
) -> Result<Vec<MediaItem>, rusqlite::Error> {
    let search_pattern = format!("%{}%", term);
    let mut sql = String::from(
        "SELECT id, title, native_title, romaji_title, year, media_type, status,
                quality_type, source, notes, tmdb_id, anilist_id, poster_url,
                created_at, updated_at FROM media_items
         WHERE (title LIKE ?1 OR notes LIKE ?1 OR native_title LIKE ?1 OR romaji_title LIKE ?1)",
    );
    let mut param_values: Vec<Box<dyn rusqlite::types::ToSql>> = Vec::new();
    param_values.push(Box::new(search_pattern));

    if let Some(mt) = media_type {
        sql.push_str(" AND media_type = ?2");
        param_values.push(Box::new(mt.to_string()));
    }
    sql.push_str(" ORDER BY title ASC");

    let params_refs: Vec<&dyn rusqlite::types::ToSql> =
        param_values.iter().map(|p| p.as_ref()).collect();
    let mut stmt = conn.prepare(&sql)?;
    let items = stmt
        .query_map(params_refs.as_slice(), |row| row_to_item(row))?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(items)
}

pub fn check_duplicate_by_id(
    conn: &Connection,
    item: &MediaItem,
) -> Result<bool, rusqlite::Error> {
    // Check by API ID first
    if item.media_type == "Anime" {
        if let Some(anilist_id) = item.anilist_id {
            let count: i64 = conn.query_row(
                "SELECT COUNT(*) FROM media_items WHERE anilist_id = ?1",
                params![anilist_id],
                |row| row.get(0),
            )?;
            if count > 0 {
                return Ok(true);
            }
        }
    } else {
        if let Some(tmdb_id) = item.tmdb_id {
            let count: i64 = conn.query_row(
                "SELECT COUNT(*) FROM media_items WHERE tmdb_id = ?1 AND media_type = ?2",
                params![tmdb_id, item.media_type],
                |row| row.get(0),
            )?;
            if count > 0 {
                return Ok(true);
            }
        }
    }

    // Fall back to title + year check
    let count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM media_items WHERE title = ?1 AND year = ?2 AND media_type = ?3",
        params![item.title, item.year, item.media_type],
        |row| row.get(0),
    )?;
    Ok(count > 0)
}

pub fn count_items_with_quality_type(
    conn: &Connection,
    quality_type: &str,
) -> Result<i64, rusqlite::Error> {
    let count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM media_items WHERE quality_type = ?1",
        params![quality_type],
        |row| row.get(0),
    )?;
    Ok(count)
}

pub fn get_counts(
    conn: &Connection,
) -> Result<std::collections::HashMap<String, i64>, rusqlite::Error> {
    let mut counts = std::collections::HashMap::new();
    let mut stmt = conn.prepare(
        "SELECT media_type, COUNT(*) FROM media_items GROUP BY media_type",
    )?;
    let rows = stmt.query_map([], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
    })?;
    for row in rows {
        let (media_type, count) = row?;
        counts.insert(media_type, count);
    }
    Ok(counts)
}
