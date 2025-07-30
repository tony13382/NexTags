import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { text } = await request.json();
    
    if (!text) {
      return NextResponse.json(
        { error: 'Text is required' },
        { status: 400 }
      );
    }

    // 在 Docker 容器內，使用容器名稱訪問後端
    const backendUrl = process.env.NODE_ENV === 'development' 
      ? 'http://backend:8000' 
      : 'http://localhost:6000';
    
    const response = await fetch(`${backendUrl}/tools/pinyin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Pinyin API route error:', error);
    return NextResponse.json(
      { error: 'Failed to convert to pinyin' },
      { status: 500 }
    );
  }
}