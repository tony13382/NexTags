# Personal Music Manager

Self-hosted music library management system with smart playlists, automated import workflows, and AI-powered lyrics processing.

Built with FastAPI and React, deployed via Docker.

## Features

### Music Library Management
- Browse and search your entire music library with multi-criteria filtering (title, folder, language, favorites)
- Inline tag editor supporting 20+ metadata fields (ID3v2 / Vorbis / FLAC)
- Cover art display and ReplayGain loudness normalization
- Support for MP3, FLAC, M4A, OGG, WAV, AAC, WMA formats

### Smart Playlists
- Create playlists with flexible include/exclude tag filters, language filters, and favorites toggle
- Multiple sort methods: title, creation time, album, artist
- Export playlists as M3U files (single or batch)
- Import/export playlist configurations as JSON for backup and sharing

### Music Import Workflow
A guided multi-step process to add new music to your library:

1. Upload audio files to a staging area
2. Auto-convert M4A to lossless FLAC (tags preserved)
3. Extract and review metadata
4. Edit tags before finalizing
5. Detect missing artist folders and upload artist images
6. Move files to the correct library path
7. Generate ReplayGain tags automatically

### AI Lyrics Processing
Uses Claude API to clean up and enhance lyrics:
- Standardize LRC time format
- Convert Simplified Chinese to Traditional Chinese
- Translate non-Chinese lyrics (English, Korean, etc.) with inline Chinese translations

### Additional Features
- **ReplayGain** - Single file or batch loudness normalization via r128gain
- **Redis Caching** - Fast tag lookups with cache statistics and rebuild tools
- **Drag-and-drop Settings** - Reorder music folders, tags, and languages
- **Playlist Config Backup** - Export/import all playlist settings

## Screenshots

> TODO: Add screenshots

## Quick Start

### Prerequisites
- Docker & Docker Compose
- A music files directory on the host machine
- (Optional) Anthropic API key for lyrics processing

### 1. Clone and configure

```bash
git clone https://github.com/your-username/Personal-MusicManager.git
cd Personal-MusicManager
cp .env.example .env
```

Edit `.env` with your settings:

```env
MUSIC_ROOT_PATH=/path/to/your/music
ANTHROPIC_TOKEN=           # Optional, for AI lyrics processing
POSTGRES_PASSWORD=your_password
```

### 2. Start the application

```bash
# Production
make prod

# Or development (with hot reload)
make dev
```

### 3. Initial setup

1. Open http://localhost:4000/settings
2. Add your music folders (e.g. Chinese, Japanese, English)
3. Configure supported tags and languages
4. Go to the cache page and rebuild the cache

The app is now ready at **http://localhost:4000**.

## Usage

### Browsing Music
Open the home page to browse your library. Use the filters at the top to search by title, folder, language, or favorites. Click any track to edit its tags inline.

### Creating Smart Playlists
Go to the Playlists page and create a new playlist. Set your filter criteria (tags, language, favorites), choose a sort order, and save. You can generate M3U files for use in any music player.

### Importing New Music
Go to the New page and upload an audio file. Follow the guided steps: review extracted tags, edit if needed, upload an artist image if it's a new artist, and confirm the final file location. ReplayGain tags are generated automatically.

### Processing Lyrics
In the tag editor, use the lyrics tool to clean up and format LRC lyrics. Requires an Anthropic API key in your `.env` file.

## Makefile Commands

```bash
make dev          # Start development environment
make prod         # Start production environment
make stop         # Stop all services
make logs         # View logs
make rebuild      # Rebuild and start dev environment
make ps           # View container status
make help         # Show all available commands
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, PostgreSQL, Redis |
| Frontend | React, Vite, TailwindCSS, shadcn/ui |
| Audio | Mutagen, FFmpeg, r128gain |
| AI | Anthropic Claude API |
| Infrastructure | Docker, Nginx |

## Project Structure

```
.
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── router/         # API endpoints
│   │   ├── dependencies/   # Business logic
│   │   ├── schemas/        # Pydantic models
│   │   └── services/       # Background tasks
│   └── config.py
├── frontend/               # React frontend
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # UI components
│   │   └── lib/            # Utilities
├── nginx/                  # Nginx config (production)
├── docker-compose.yml      # Production compose
├── docker-compose.dev.yml  # Development compose
└── Makefile
```

## Development

See [Development Guide](README.dev.md) for detailed setup, hot reload configuration, and debugging tips.

See [Production Deployment](README.prod.md) for production-specific instructions.

## API Documentation

With the backend running, visit:
- Swagger UI: http://localhost:6000/docs
- ReDoc: http://localhost:6000/redoc

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Issues and pull requests are welcome!
