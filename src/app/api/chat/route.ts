import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    if (!process.env.BACKEND_URL) {
      throw new Error('BACKEND_URL environment variable is not set');
    }

    const body = await req.json();
    const { message, document_id, chat_history } = body;

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    const response = await fetch(`${process.env.BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        documentId: document_id,
        chatHistory: chat_history
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('Backend error:', error);
      throw new Error('Failed to get response from backend');
    }

    const data = await response.json();

    return NextResponse.json({
      id: crypto.randomUUID(),
      content: data.answer,
      sources: data.sources,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Chat error:', error);
    return NextResponse.json(
      { 
        error: error instanceof Error ? error.message : 'Failed to process chat message'
      },
      { status: 500 }
    );
  }
}
