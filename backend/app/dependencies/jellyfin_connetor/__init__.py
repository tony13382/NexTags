"""
Jellyfin 連接器模組

提供與 Jellyfin 媒體伺服器互動的功能，包括：
- 歌曲搜尋和資訊取得
- 播放清單搜尋和操作

使用方式:
    from app.dependencies.jellyfin_connetor import songs, playlists
    
    # 搜尋歌曲
    results = await songs.search_songs("歌曲名稱")
    
    # 取得播放清單
    playlists_list = await playlists.get_playlists()
"""

from .songs import (
    JellyfinSongsClient,
    jellyfin_songs,
    search_songs,
    get_song_by_id,
    get_songs_by_artist,
    get_songs_by_album,
    get_song_stream_url
)

from .playlists import (
    JellyfinPlaylistsClient,
    jellyfin_playlists,
    get_playlists,
    search_playlists,
    get_playlist_by_id,
    get_playlist_items,
    create_playlist,
    add_songs_to_playlist,
    remove_songs_from_playlist,
    clear_playlist,
    update_playlist,
    delete_playlist
)

from .auth import (
    JellyfinAuthClient,
    jellyfin_auth,
    get_access_token,
    get_authenticated_user_id,
    get_auth_headers
)

__all__ = [
    # Songs 相關
    "JellyfinSongsClient",
    "jellyfin_songs",
    "search_songs",
    "get_song_by_id",
    "get_songs_by_artist",
    "get_songs_by_album",
    "get_song_stream_url",
    
    # Playlists 相關
    "JellyfinPlaylistsClient",
    "jellyfin_playlists",
    "get_playlists",
    "search_playlists",
    "get_playlist_by_id",
    "get_playlist_items",
    "create_playlist",
    "add_songs_to_playlist",
    "remove_songs_from_playlist",
    "clear_playlist",
    "update_playlist",
    "delete_playlist",
    
    # Auth 相關
    "JellyfinAuthClient",
    "jellyfin_auth",
    "get_access_token",
    "get_authenticated_user_id",
    "get_auth_headers"
]

# 版本資訊
__version__ = "0.1.0"
__author__ = "Personal Music Manager"
__description__ = "Jellyfin API 連接器，提供歌曲和播放清單操作功能"