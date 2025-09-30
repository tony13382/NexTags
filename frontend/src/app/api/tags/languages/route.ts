import { NextResponse } from 'next/server';

export async function GET() {
    try {
        // 使用環境變數或預設值來設定後端 URL
        const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

        const response = await fetch(`${backendUrl}/tags/languages`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const languages = await response.json();
        return NextResponse.json(languages);
    } catch (error) {
        console.error('Languages API route error:', error);
        return NextResponse.json(
            { error: '無法取得語言清單' },
            { status: 500 }
        );
    }
}