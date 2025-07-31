import { NextResponse } from 'next/server';

export async function GET() {
    try {
        // 在 Docker 容器內，使用容器名稱訪問後端
        const backendUrl = process.env.NODE_ENV === 'development'
            ? 'http://backend:8000'
            : 'http://localhost:6000';

        const response = await fetch(`${backendUrl}/tags/baseFolders`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const baseFolders = await response.json();
        return NextResponse.json(baseFolders);
    } catch (error) {
        console.error('BaseFolders API route error:', error);
        return NextResponse.json(
            { error: '無法取得基礎資料夾清單' },
            { status: 500 }
        );
    }
}