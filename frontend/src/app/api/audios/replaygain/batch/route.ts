import { NextResponse } from 'next/server';

export async function POST() {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://backend:8000';

    const response = await fetch(`${backendUrl}/audios/replaygain/batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { success: false, message: data.detail || '批量生成 ReplayGain 失敗' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('批量生成 ReplayGain 錯誤:', error);
    return NextResponse.json(
      { success: false, message: '批量生成 ReplayGain 時發生錯誤' },
      { status: 500 }
    );
  }
}
