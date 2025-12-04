# Media Tracker

A PyQt6-based desktop application for tracking your media collection (Movies, TV Shows, and Anime). Keep track of what you have on your drives, what you want to download, and what you're working on - all with an easy-to-use spreadsheet-like interface.

## Features

- **Three Media Types**: Separate tabs for Movies, TV Shows, and Anime
- **Organization**: Each media type has three categories:
  - **On Drive**: Media you already have
  - **To Download**: Media you want to acquire
  - **To Work On**: Media you're currently processing (remuxing, encoding, etc.)
- **Spreadsheet Interface**: Sort and search through your collection easily
- **Online Search**: Integrate with TMDB (Movies/TV) and AniList (Anime) to auto-fill metadata
- **Quality Tracking**: Track quality types (Remux, WebDL, BluRay, etc.)
- **Source Tracking**: Remember where you got each item
- **Notes**: Add custom notes to any item
- **Move Between Categories**: Right-click to move items between On Drive/To Download/To Work On
- **Duplicate Detection**: Get warned if you're adding something you already have
- **SQLite Database**: All data stored locally in a simple database file

## Installation

### Prerequisites

- Python 3.8 or higher

### Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd media-tracker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:

**Option 1 (Recommended):**
```bash
python run.py
```

**Option 2:**
```bash
python src/main.py
```

## Configuration

### TMDB API Key (Optional but Recommended)

To enable auto-fill for Movies and TV Shows:

1. Create a free account at [TheMovieDB.org](https://www.themoviedb.org/)
2. Go to [Settings > API](https://www.themoviedb.org/settings/api)
3. Request an API key (choose "Developer" option)
4. In the application, click **"TMDB API Key"** in the toolbar
5. Paste your API key

**Note**: AniList doesn't require an API key!

## Usage

### Adding Media

1. Click **"Add Item"** in the toolbar
2. (Optional) Search for the title using the online database
3. Double-click a search result to auto-fill title and year
4. Fill in additional details:
   - **Status**: On Drive / To Download / To Work On
   - **Quality Type**: Remux, WebDL, BluRay, etc.
   - **Source**: Where you got it (optional)
   - **Notes**: Any additional info (optional)
5. Click **"Save"**

### Editing Media

- **Double-click** any item in the table to edit it
- Or **right-click** and select **"Edit"**

### Moving Between Categories

- **Right-click** an item
- Select **"Move to"** → Choose the new category (On Drive / To Download / To Work On)

### Searching

- Use the search bar at the top to filter by title or notes
- Search works within the currently selected media type (Movies/TV/Anime)
- Click **"Clear"** to reset the search

### Sorting

- Click any column header to sort by that column
- Click again to reverse the sort order

### Deleting Media

- **Right-click** an item and select **"Delete"**
- Confirm the deletion

## Database

The SQLite database is stored at `data/media_tracker.db`. This file contains all your tracked media.

**Backup Tip**: Periodically copy the `data/` folder to back up your collection!

## Quality Types

Common quality types you might use:
- **Remux**: Full quality rip from BluRay/UHD disc
- **WebDL**: Downloaded from streaming service
- **BluRay**: BluRay encode
- **Remux 1080p** / **Remux 2160p**: Size-specific remuxes
- **WEB-DL 1080p** / **WEB-DL 2160p**: Size-specific web downloads

The quality field is editable, so you can add your own custom values!

## Tips

1. **Use the Notes field** to track:
   - Audio tracks (e.g., "Atmos, DTS-HD MA")
   - Subtitle status
   - Any issues or todos
   - File size

2. **Quality Type + Source** together give you the full picture of each item

3. **Search is fast** - use it to quickly find items rather than scrolling

4. **Move between categories** as you progress:
   - Start in "To Download"
   - Move to "To Work On" when processing
   - Move to "On Drive" when complete

## Project Structure

```
media-tracker/
├── src/
│   ├── main.py                 # Application entry point
│   ├── ui/
│   │   ├── main_window.py      # Main window with tabs
│   │   ├── media_table.py      # Reusable table widget
│   │   └── dialogs/
│   │       └── edit_dialog.py  # Add/edit dialog
│   ├── database/
│   │   ├── db_manager.py       # SQLite operations
│   │   └── models.py           # Data models
│   ├── api/
│   │   ├── tmdb_client.py      # TMDB API integration
│   │   └── anilist_client.py   # AniList API integration
│   └── utils/                  # Helper functions
├── data/                       # SQLite database
├── requirements.txt
└── README.md
```

## Troubleshooting

### "TMDB API key not configured"

You need to add your TMDB API key. See the [Configuration](#tmdb-api-key-optional-but-recommended) section above.

### Search isn't finding my item

- Make sure you're on the correct media type tab (Movies/TV/Anime)
- Try a different search term or partial title
- The item might not be in the online database

### Application won't start

Make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

## Future Enhancements

Possible features to add:
- Import/Export to CSV
- Statistics dashboard (total remuxes, storage estimates, etc.)
- Poster thumbnails in the table
- Custom fields
- AniDB integration (if needed)
- Advanced filtering (e.g., show only Remuxes)

## License

MIT License - feel free to modify and use for your own purposes!