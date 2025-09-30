import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    try {
        const { lyric } = await request.json();

        if (!lyric) {
            return NextResponse.json(
                { error: 'Lyric is required' },
                { status: 400 }
            );
        }

        // 使用環境變數或預設值來設定後端 URL
        const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

        const response = await fetch(`${backendUrl}/tools/lyric`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lyric })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        return NextResponse.json(data);
    } catch (error) {
        console.error('Lyric API route error:', error);
        return NextResponse.json(
            { error: 'Failed to process lyric' },
            { status: 500 }
        );
    }
}