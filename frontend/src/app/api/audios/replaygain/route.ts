import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://backend:8000';

    const response = await fetch(`${backendUrl}/audios/replaygain`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { success: false, message: data.detail || '生成 ReplayGain 失敗', path: body.path },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('生成 ReplayGain 錯誤:', error);
    return NextResponse.json(
      { success: false, message: '生成 ReplayGain 時發生錯誤' },
      { status: 500 }
    );
  }
}
