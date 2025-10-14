import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || 'http://backend:8000';

// Set route config to increase timeout and disable static optimization
export const dynamic = 'force-dynamic';
export const maxDuration = 300; // 5 minutes

export async function POST(_request: NextRequest) {
    console.log('[Frontend API] Received POST request to generate-all-m3u');
    console.log('[Frontend API] Backend URL:', BACKEND_URL);

    try {
        const startTime = Date.now();
        console.log('[Frontend API] Sending request to backend...');

        // 轉發請求到後端
        const backendResponse = await fetch(`${BACKEND_URL}/playlists/generate-all-m3u`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            cache: 'no-store',
        });

        const elapsed = Date.now() - startTime;
        console.log(`[Frontend API] Backend responded in ${elapsed}ms with status ${backendResponse.status}`);

        if (!backendResponse.ok) {
            throw new Error(`Backend request failed: ${backendResponse.status}`);
        }

        const responseData = await backendResponse.json();
        console.log('[Frontend API] Response data:', responseData);

        return NextResponse.json(responseData, {
            status: backendResponse.status,
        });

    } catch (error) {
        console.error('[Frontend API] Error generating all M3U files:', error);
        return NextResponse.json(
            {
                success: false,
                message: '批量生成 M3U 檔案失敗',
                error: error instanceof Error ? error.message : String(error)
            },
            { status: 500 }
        );
    }
}