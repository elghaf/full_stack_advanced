import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Forward the request to FastAPI backend
    const response = await fetch('http://localhost:8000/api/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || 'Error processing chat message' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Error processing chat message:', error);
    return NextResponse.json(
      { error: 'Error processing chat message' },
      { status: 500 }
    );
  }
}
