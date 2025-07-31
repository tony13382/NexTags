import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const playlistIndex = params.id;

        const response = await fetch(`${BACKEND_URL}/playlists/${playlistIndex}/songs`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            cache: 'no-store',
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Error fetching playlist songs:', error);
        return NextResponse.json(
            {
                success: false,
                message: '獲取播放清單歌曲失敗',
                error: error instanceof Error ? error.message : String(error)
            },
            { status: 500 }
        );
    }
}