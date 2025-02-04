import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    if (!process.env.BACKEND_URL) {
      throw new Error('BACKEND_URL environment variable is not set');
    }

    const formData = await req.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { success: false, error: 'No file provided' },
        { status: 400 }
      );
    }

    const response = await fetch(`${process.env.BACKEND_URL}/files/`, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { 
          success: false, 
          error: data?.detail || data?.error || data?.message || 'Upload failed'
        },
        { status: response.status }
      );
    }

    if (!data?.document) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Invalid response from server: missing document data'
        },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      document: {
        id: data.document.id || '',
        name: data.document.name || '',
        type: data.document.type || '',
        size: data.document.size || 0,
        uploadedAt: data.document.uploadedAt || new Date().toISOString(),
        pageCount: data.document.pageCount || 1,
        previewUrls: data.document.previewUrls || []
      }
    });

  } catch (error) {
    console.error('Error in file upload:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      },
      { status: 500 }
    );
  }
}