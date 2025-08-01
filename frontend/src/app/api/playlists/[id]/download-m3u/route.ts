import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id: playlistIndex } = await params;

        // 首先獲取播放清單的歌曲資料
        const songsResponse = await fetch(`${BACKEND_URL}/playlists/${playlistIndex}/songs`, {
            headers: {
                'Content-Type': 'application/json',
            },
            cache: 'no-store',
        });

        if (!songsResponse.ok) {
            throw new Error(`Failed to fetch playlist songs: ${songsResponse.status}`);
        }

        const songsData = await songsResponse.json();

        if (!songsData.success) {
            throw new Error(songsData.message || '獲取播放清單歌曲失敗');
        }

        // 生成 M3U 文件內容
        const playlistName = songsData.playlist_name || `Playlist_${playlistIndex}`;
        let m3uContent = `#EXTM3U\n#EXTENC:UTF-8\n#PLAYLIST:${playlistName}\n\n`;

        songsData.songs.forEach((song: any) => {
            if (song.file_path) {
                // 添加歌曲資訊
                const songName = song.song_name || song.file_path.split('/').pop() || 'Unknown';
                m3uContent += `#EXTINF:-1,${songName}\n`;
                m3uContent += `${song.file_path}\n\n`;
            }
        });

        // 設定檔案下載的回應標頭
        const fileName = `${playlistName.replace(/[^a-zA-Z0-9_\-\u4e00-\u9fff]/g, '_')}.m3u`;

        // 將 M3U 內容轉換為 UTF-8 編碼的 Buffer
        const m3uBuffer = Buffer.from(m3uContent, 'utf8');

        return new NextResponse(m3uBuffer, {
            status: 200,
            headers: {
                'Content-Type': 'audio/x-mpegurl; charset=utf-8',
                'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(fileName)}`,
                'Cache-Control': 'no-cache',
            },
        });

    } catch (error) {
        console.error('Error generating M3U file:', error);
        return NextResponse.json(
            {
                success: false,
                message: '生成 M3U 檔案失敗',
                error: error instanceof Error ? error.message : String(error)
            },
            { status: 500 }
        );
    }
}