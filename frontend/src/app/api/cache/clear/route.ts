import { NextResponse } from 'next/server';

export async function DELETE() {
    try {
        // 使用環境變數或預設值來設定後端 URL
        const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

        const response = await fetch(`${backendUrl}/cache/clear`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error(`Backend responded with status: ${response.status}`);
        }

        const data = await response.json();
        return NextResponse.json(data);

    } catch (error) {
        console.error('清空快取失敗:', error);
        return NextResponse.json(
            { error: '清空快取失敗' },
            { status: 500 }
        );
    }
}