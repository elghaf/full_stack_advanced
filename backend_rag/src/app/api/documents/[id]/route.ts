import { NextRequest, NextResponse } from 'next/server';

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Await the params to satisfy Next.js async requirement
    const { id } = await Promise.resolve(params);
    
    if (!id) {
      return NextResponse.json(
        { error: 'Document ID is required' },
        { status: 400 }
      );
    }

    const backendUrl = process.env.BACKEND_URL;
    const response = await fetch(
      `${backendUrl}/api/documents/${id}`,
      {
        method: 'DELETE',
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to delete document');
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Delete error:', error);
    return NextResponse.json(
      { 
        success: false,
        error: error instanceof Error ? error.message : 'Failed to delete document'
      },
      { status: 500 }
    );
  }
} 