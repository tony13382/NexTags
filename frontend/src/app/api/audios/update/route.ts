import { NextRequest, NextResponse } from 'next/server';

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    
    // 在 Docker 容器內，使用容器名稱訪問後端
    const backendUrl = process.env.NODE_ENV === 'development' 
      ? 'http://backend:8000' 
      : 'http://localhost:6000';
    
    const response = await fetch(`${backendUrl}/audios/update`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Update tags API route error:', error);
    return NextResponse.json(
      { error: 'Failed to update tags' },
      { status: 500 }
    );
  }
}