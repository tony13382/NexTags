import { NextResponse } from 'next/server';

export async function GET() {
    try {
        // 使用環境變數或預設值來設定後端 URL
        const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

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