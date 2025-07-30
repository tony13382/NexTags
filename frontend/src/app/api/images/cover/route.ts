import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const path = searchParams.get('path');

    if (!path) {
        return NextResponse.json({ error: '缺少 path 參數' }, { status: 400 });
    }

    try {
        // 代理到後端 API
        const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';
        const response = await fetch(`${backendUrl}/images/cover?path=${encodeURIComponent(path)}`);

        if (!response.ok) {
            if (response.status === 404) {
                return NextResponse.json({ error: '圖片檔案不存在' }, { status: 404 });
            }
            return NextResponse.json({ error: '無法載入圖片' }, { status: response.status });
        }

        const imageBuffer = await response.arrayBuffer();
        const contentType = response.headers.get('content-type') || 'image/jpeg';

        return new NextResponse(imageBuffer, {
            status: 200,
            headers: {
                'Content-Type': contentType,
                'Cache-Control': 'public, max-age=3600',
            },
        });

    } catch (error) {
        console.error('圖片代理錯誤:', error);
        return NextResponse.json({ error: '伺服器錯誤' }, { status: 500 });
    }
}