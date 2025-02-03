import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    
    const response = await fetch('http://localhost:8000/api/files/', {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.message || `Upload failed with status: ${response.status}`);
    }

    return NextResponse.json({
      success: true,
      message: 'File uploaded successfully',
      data
    });
  } catch (error) {
    console.error('Error in file upload:', error);
    return NextResponse.json(
      { 
        success: false,
        message: error instanceof Error ? error.message : 'Upload failed',
      },
      { status: 500 }
    );
  }
}