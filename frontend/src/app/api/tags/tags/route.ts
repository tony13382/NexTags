import { NextResponse } from 'next/server';

export async function GET() {
    try {
        // 使用環境變數或預設值來設定後端 URL
        const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

        const response = await fetch(`${backendUrl}/tags/tags`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const tags = await response.json();
        return NextResponse.json(tags);
    } catch (error) {
        console.error('Tags API route error:', error);
        return NextResponse.json(
            { error: '無法取得標籤清單' },
            { status: 500 }
        );
    }
}