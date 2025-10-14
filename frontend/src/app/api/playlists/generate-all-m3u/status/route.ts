import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || 'http://backend:8000';

export async function GET(_request: NextRequest) {
    try {
        // 轉發請求到後端
        const backendResponse = await fetch(`${BACKEND_URL}/playlists/generate-all-m3u/status`, {
            method: 'GET',
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
        console.error('Error fetching batch generation status:', error);
        return NextResponse.json(
            {
                status: 'error',
                message: '查詢批量生成狀態失敗',
                error: error instanceof Error ? error.message : String(error)
            },
            { status: 500 }
        );
    }
}
