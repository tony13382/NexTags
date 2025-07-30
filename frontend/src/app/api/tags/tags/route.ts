import { NextResponse } from 'next/server';

export async function GET() {
    try {
        // 在 Docker 容器內，使用容器名稱訪問後端
        const backendUrl = process.env.NODE_ENV === 'development'
            ? 'http://backend:8000'
            : 'http://localhost:6000';

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