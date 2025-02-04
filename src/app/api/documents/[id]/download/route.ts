import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const id = params?.id;
  if (!id) {
    return NextResponse.json(
      { error: 'Document ID is required' },
      { status: 400 }
    );
  }

  try {
    const backendUrl = process.env.BACKEND_URL;
    const response = await fetch(
      `${backendUrl}/api/documents/${id}/download`,
      {
        method: 'GET',
      }
    );

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    // Get the file content as array buffer
    const fileBuffer = await response.arrayBuffer();
    
    // Get content type and filename from backend response
    const contentType = response.headers.get('content-type') || 'application/octet-stream';
    const contentDisposition = response.headers.get('content-disposition');
    const filename = contentDisposition?.split('filename=')[1]?.replace(/['"]/g, '') || 'document';

    // Return the file with appropriate headers
    return new NextResponse(fileBuffer, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error('Download error:', error);
    return NextResponse.json(
      { error: 'Failed to download document' },
      { status: 500 }
    );
  }
} 