import { NextResponse } from 'next/server';

export async function GET() {
    try {
        // 在 Docker 容器內，使用容器名稱訪問後端
        const backendUrl = process.env.NODE_ENV === 'development'
            ? 'http://backend:8000'
            : 'http://localhost:6000';

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