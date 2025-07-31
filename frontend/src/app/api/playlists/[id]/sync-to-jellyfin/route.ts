import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const playlistIndex = params.id;

        const response = await fetch(`${BACKEND_URL}/playlists/${playlistIndex}/sync-to-jellyfin`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            cache: 'no-store',
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(
                errorData?.detail ||
                `HTTP error! status: ${response.status}`
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Error syncing playlist to Jellyfin:', error);
        return NextResponse.json(
            {
                success: false,
                message: '同步播放清單到 Jellyfin 失敗',
                error: error instanceof Error ? error.message : String(error)
            },
            { status: 500 }
        );
    }
}