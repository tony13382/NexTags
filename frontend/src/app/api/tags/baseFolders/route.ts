import { NextResponse } from 'next/server';

export async function GET() {
    try {
        // 在 Docker 容器內，使用服務名稱訪問同網絡的後端服務
        const backendUrl = process.env.NODE_ENV === 'development'
            ? 'http://backend:8000'
            : 'http://localhost:6000';

        const response = await fetch(`${backendUrl}/tags/baseFolders`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const baseFolders = await response.json();

        // 包裝成前端期望的格式
        return NextResponse.json({
            success: true,
            base_folders: baseFolders
        });
    } catch (error) {
        console.error('BaseFolders API route error:', error);
        return NextResponse.json(
            { error: '無法取得基礎資料夾清單' },
            { status: 500 }
        );
    }
}