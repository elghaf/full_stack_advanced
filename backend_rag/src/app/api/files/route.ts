import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { success: false, error: 'No file provided' },
        { status: 400 }
      );
    }

    console.log('Uploading file:', file.name, 'Size:', file.size, 'Type:', file.type); // Debug log

    const response = await fetch('http://localhost:8000/api/files', {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();
    console.log('Backend response:', data); // Debug log

    if (!response.ok) {
      throw new Error(data.detail || data.message || `Upload failed with status: ${response.status}`);
    }

    return NextResponse.json({
      success: true,
      document: {
        id: data.document?.id || '',
        name: file.name,
        type: file.type,
        size: file.size,
        uploadedAt: new Date().toISOString(),
        pageCount: data.document?.pageCount || 1,
        previewUrls: data.document?.previewUrls || []
      }
    });

  } catch (error) {
    console.error('Error in file upload:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Upload failed'
      },
      { status: 500 }
    );
  }
}