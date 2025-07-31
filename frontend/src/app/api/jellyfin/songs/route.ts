import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
    try {
        const { searchParams } = new URL(request.url);
        const params = new URLSearchParams();

        // 轉發所有查詢參數
        searchParams.forEach((value, key) => {
            params.append(key, value);
        });

        // 在 Docker 容器內，使用容器名稱訪問後端
        const backendUrl = process.env.NODE_ENV === 'development'
            ? 'http://backend:8000'
            : 'http://localhost:6000';

        const response = await fetch(`${backendUrl}/jellyfin/songs?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        return NextResponse.json(data);
    } catch (error) {
        console.error('Jellyfin API route error:', error);
        return NextResponse.json(
            { error: 'Failed to fetch Jellyfin songs' },
            { status: 500 }
        );
    }
}