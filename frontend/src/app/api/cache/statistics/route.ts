import { NextResponse } from 'next/server';

export async function GET() {
    try {
        // 在 Docker 容器內，使用容器名稱訪問後端
        const backendUrl = process.env.NODE_ENV === 'development'
            ? 'http://backend:8000'
            : 'http://localhost:6000';

        const response = await fetch(`${backendUrl}/cache/statistics`);

        if (!response.ok) {
            throw new Error(`Backend responded with status: ${response.status}`);
        }

        const data = await response.json();
        return NextResponse.json(data);

    } catch (error) {
        console.error('獲取快取統計失敗:', error);
        return NextResponse.json(
            { error: '獲取快取統計失敗' },
            { status: 500 }
        );
    }
}