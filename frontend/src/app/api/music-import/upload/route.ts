import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
    try {
        // 使用環境變數或預設值來設定後端 URL
        const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';

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