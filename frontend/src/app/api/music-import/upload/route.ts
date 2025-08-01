import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
    try {
        // 在 Docker 容器內，使用服務名稱訪問同網絡的後端服務
        const backendUrl = process.env.NODE_ENV === 'development'
            ? 'http://backend:8000'
            : 'http://localhost:6000';

        const formData = await request.formData()

        const response = await fetch(`${backendUrl}/music-import/upload`, {
            method: 'POST',
            body: formData,
        })

        const data = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        return NextResponse.json(data)
    } catch (error) {
        console.error('Music import upload error:', error)
        return NextResponse.json(
            { success: false, detail: '檔案上傳失敗' },
            { status: 500 }
        )
    }
}