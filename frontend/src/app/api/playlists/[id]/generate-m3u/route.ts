import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || 'http://backend:8000';

export async function POST(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id: playlistIndex } = await params;

        // 轉發請求到後端
        const backendResponse = await fetch(`${BACKEND_URL}/playlists/${playlistIndex}/generate-m3u`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            cache: 'no-store',
        });

        if (!backendResponse.ok) {
            throw new Error(`Backend request failed: ${backendResponse.status}`);
        }

        const responseData = await backendResponse.json();

        return NextResponse.json(responseData, {
            status: backendResponse.status,
        });

    } catch (error) {
        console.error('Error generating M3U file to filesystem:', error);
        return NextResponse.json(
            {
                success: false,
                message: '生成 M3U 檔案到檔案系統失敗',
                error: error instanceof Error ? error.message : String(error)
            },
            { status: 500 }
        );
    }
}