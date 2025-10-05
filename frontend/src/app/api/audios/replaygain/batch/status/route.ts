import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://backend:8000';

    const response = await fetch(`${backendUrl}/audios/replaygain/batch/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { success: false, message: data.detail || '查詢進度失敗' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('查詢 ReplayGain 進度錯誤:', error);
    return NextResponse.json(
      { success: false, message: '查詢進度時發生錯誤' },
      { status: 500 }
    );
  }
}
