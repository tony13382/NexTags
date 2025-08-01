import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000'

export async function GET(
    request: NextRequest,
    { params }: { params: { endpoint: string[] } }
) {
    try {
        const endpoint = params.endpoint.join('/')
        const searchParams = new URL(request.url).searchParams
        const queryString = searchParams.toString()

        const url = `${BACKEND_URL}/music-import/${endpoint}${queryString ? `?${queryString}` : ''}`

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        })

        const data = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        return NextResponse.json(data)
    } catch (error) {
        console.error('Music import API error:', error)
        return NextResponse.json(
            { success: false, detail: 'API 請求失敗' },
            { status: 500 }
        )
    }
}

export async function POST(
    request: NextRequest,
    { params }: { params: { endpoint: string[] } }
) {
    try {
        const endpoint = params.endpoint.join('/')

        let body: any
        let headers: Record<string, string> = {}

        // 檢查是否是 FormData (用於文件上傳)
        const contentType = request.headers.get('content-type')
        if (contentType?.includes('multipart/form-data')) {
            body = await request.formData()
        } else {
            body = JSON.stringify(await request.json())
            headers['Content-Type'] = 'application/json'
        }

        const response = await fetch(`${BACKEND_URL}/music-import/${endpoint}`, {
            method: 'POST',
            headers,
            body,
        })

        const data = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        return NextResponse.json(data)
    } catch (error) {
        console.error('Music import API error:', error)
        return NextResponse.json(
            { success: false, detail: 'API 請求失敗' },
            { status: 500 }
        )
    }
}

export async function PUT(
    request: NextRequest,
    { params }: { params: { endpoint: string[] } }
) {
    try {
        const endpoint = params.endpoint.join('/')
        const body = await request.json()

        const response = await fetch(`${BACKEND_URL}/music-import/${endpoint}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        })

        const data = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        return NextResponse.json(data)
    } catch (error) {
        console.error('Music import API error:', error)
        return NextResponse.json(
            { success: false, detail: 'API 請求失敗' },
            { status: 500 }
        )
    }
}

export async function DELETE(
    request: NextRequest,
    { params }: { params: { endpoint: string[] } }
) {
    try {
        const endpoint = params.endpoint.join('/')
        const body = await request.json()

        const response = await fetch(`${BACKEND_URL}/music-import/${endpoint}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        })

        const data = await response.json()

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status })
        }

        return NextResponse.json(data)
    } catch (error) {
        console.error('Music import API error:', error)
        return NextResponse.json(
            { success: false, detail: 'API 請求失敗' },
            { status: 500 }
        )
    }
}