"""
Jellyfin 連接器使用範例

此檔案展示如何使用 Jellyfin 連接器的各種功能
"""

import asyncio
from app.dependencies.jellyfin_connetor import songs, playlists
from app.dependencies.logger import logger


async def example_songs_operations():
    """歌曲操作範例"""
    logger.info("=== 歌曲操作範例 ===")
    
    # 1. 搜尋歌曲
    print("1. 搜尋歌曲...")
    search_results = await songs.search_songs("love", limit=5)
    print(f"找到 {len(search_results)} 首歌曲:")
    for song in search_results:
        print(f"  - {song.get('Name')} by {', '.join(song.get('Artists', []))}")
    
    if search_results:
        # 2. 取得第一首歌曲的詳細資訊
        first_song_id = search_results[0].get('Id')
        print(f"\n2. 取得歌曲詳細資訊 (ID: {first_song_id})...")
        song_detail = await songs.get_song_by_id(first_song_id)
        if song_detail:
            print(f"  歌曲名稱: {song_detail.get('Name')}")
            print(f"  演出者: {', '.join(song_detail.get('Artists', []))}")
            print(f"  專輯: {song_detail.get('Album')}")
            print(f"  年份: {song_detail.get('ProductionYear')}")
            print(f"  流派: {', '.join(song_detail.get('Genres', []))}")
        
        # 3. 取得串流 URL
        print(f"\n3. 取得串流 URL...")
        stream_url = await songs.get_song_stream_url(first_song_id, format="mp3", bitrate=320000)
        if stream_url:
            print(f"  串流 URL: {stream_url}")
    
    # 4. 根據演出者搜尋歌曲
    print(f"\n4. 根據演出者搜尋歌曲...")
    artist_songs = await songs.get_songs_by_artist("Taylor Swift", limit=3)
    print(f"找到 Taylor Swift 的 {len(artist_songs)} 首歌曲:")
    for song in artist_songs:
        print(f"  - {song.get('Name')} ({song.get('Album')})")
    
    # 5. 根據專輯搜尋歌曲
    print(f"\n5. 根據專輯搜尋歌曲...")
    album_songs = await songs.get_songs_by_album("1989", limit=3)
    print(f"找到專輯 '1989' 的 {len(album_songs)} 首歌曲:")
    for song in album_songs:
        print(f"  - {song.get('Name')} by {', '.join(song.get('Artists', []))}")


async def example_playlists_operations():
    """播放清單操作範例"""
    logger.info("=== 播放清單操作範例 ===")
    
    # 1. 取得所有播放清單
    print("1. 取得所有播放清單...")
    all_playlists = await playlists.get_playlists()
    print(f"找到 {len(all_playlists)} 個播放清單:")
    for playlist in all_playlists[:5]:  # 只顯示前5個
        print(f"  - {playlist.get('Name')} ({playlist.get('ChildCount', 0)} 首歌曲)")
    
    # 2. 搜尋播放清單
    print(f"\n2. 搜尋播放清單...")
    search_results = await playlists.search_playlists("favorites", limit=3)
    print(f"找到 {len(search_results)} 個包含 'favorites' 的播放清單:")
    for playlist in search_results:
        print(f"  - {playlist.get('Name')}: {playlist.get('Overview', '無描述')}")
    
    if all_playlists:
        # 3. 取得第一個播放清單的詳細資訊
        first_playlist = all_playlists[0]
        playlist_id = first_playlist.get('Id')
        print(f"\n3. 取得播放清單詳細資訊: {first_playlist.get('Name')}")
        playlist_detail = await playlists.get_playlist_by_id(playlist_id)
        if playlist_detail:
            print(f"  名稱: {playlist_detail.get('Name')}")
            print(f"  描述: {playlist_detail.get('Overview', '無描述')}")
            print(f"  歌曲數量: {playlist_detail.get('ChildCount', 0)}")
            print(f"  建立日期: {playlist_detail.get('DateCreated')}")
        
        # 4. 取得播放清單中的歌曲
        print(f"\n4. 取得播放清單歌曲 (前3首)...")
        playlist_songs = await playlists.get_playlist_items(playlist_id, limit=3)
        print(f"播放清單包含 {len(playlist_songs)} 首歌曲:")
        for song in playlist_songs:
            print(f"  - {song.get('Name')} by {', '.join(song.get('Artists', []))}")
    
    # 5. 建立新的播放清單（示範用）
    print(f"\n5. 建立新播放清單...")
    new_playlist_id = await playlists.create_playlist(
        name="測試播放清單",
        description="這是一個使用 API 建立的測試播放清單"
    )
    if new_playlist_id:
        print(f"  成功建立播放清單，ID: {new_playlist_id}")
        
        # 6. 更新播放清單資訊
        print(f"\n6. 更新播放清單資訊...")
        update_success = await playlists.update_playlist(
            new_playlist_id,
            name="更新後的測試播放清單",
            description="這個描述已經被更新了"
        )
        if update_success:
            print("  播放清單資訊更新成功")
        
        # 7. 刪除測試播放清單
        print(f"\n7. 刪除測試播放清單...")
        delete_success = await playlists.delete_playlist(new_playlist_id)
        if delete_success:
            print("  測試播放清單刪除成功")


async def example_integration_operations():
    """整合操作範例：搜尋歌曲並添加到播放清單"""
    logger.info("=== 整合操作範例 ===")
    
    print("1. 搜尋流行歌曲...")
    pop_songs = await songs.search_songs("pop", limit=3)
    
    if pop_songs:
        song_ids = [song.get('Id') for song in pop_songs]
        print(f"找到 {len(pop_songs)} 首流行歌曲")
        
        # 建立包含這些歌曲的播放清單
        print(f"\n2. 建立包含這些歌曲的播放清單...")
        playlist_id = await playlists.create_playlist(
            name="我的流行歌曲",
            description="包含搜尋到的流行歌曲",
            song_ids=song_ids
        )
        
        if playlist_id:
            print(f"成功建立播放清單，ID: {playlist_id}")
            
            # 驗證播放清單內容
            print(f"\n3. 驗證播放清單內容...")
            playlist_content = await playlists.get_playlist_items(playlist_id)
            print(f"播放清單包含 {len(playlist_content)} 首歌曲:")
            for song in playlist_content:
                print(f"  - {song.get('Name')} by {', '.join(song.get('Artists', []))}")
            
            # 清理：刪除示範播放清單
            print(f"\n4. 清理：刪除示範播放清單...")
            await playlists.delete_playlist(playlist_id)
            print("示範播放清單已刪除")


async def run_all_examples():
    """執行所有範例"""
    try:
        await example_songs_operations()
        print("\n" + "="*50 + "\n")
        
        await example_playlists_operations()
        print("\n" + "="*50 + "\n")
        
        await example_integration_operations()
        
    except Exception as e:
        logger.error(f"執行範例時發生錯誤: {str(e)}")
        print(f"錯誤: {str(e)}")


if __name__ == "__main__":
    print("Jellyfin 連接器使用範例")
    print("請確保已正確設定 .env 檔案中的 Jellyfin 連接資訊")
    print("="*50)
    
    # 執行範例
    asyncio.run(run_all_examples())