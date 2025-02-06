import { NextRequest, NextResponse } from 'next/server';

interface Source {
  document_id: string;
  page: number;
  start_line?: number;
  end_line?: number;
  preview?: string;
  relevance_score: number;
}

interface ChatResponse {
  answer: string;
  sources: Source[];
}

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

    // Format chat history to match backend expectations
    const formattedChatHistory = chat_history?.map((msg: any) => ({
      sender: msg.sender || (msg.isUser ? 'user' : 'ai'),
      content: msg.content || msg.text || '',
    }));

    const response = await fetch(`${process.env.BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        documentId: document_id,
        chatHistory: formattedChatHistory || []
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('Backend error:', error);
      throw new Error('Failed to get response from backend');
    }

    const data: ChatResponse = await response.json();

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
