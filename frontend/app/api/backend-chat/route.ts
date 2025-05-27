// frontend/app/api/backend-chat/route.ts
import { NextRequest, NextResponse } from 'next/server';

// Configure your backend URL (can use env variables)
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    // Read the request body
    const body = await req.json();
    
    // Choose single or batch endpoint based on request body
    const endpoint = Array.isArray(body) ? '/api/chat/batch' : '/api/chat';
    // Determine auth header: prefer incoming Authorization or cookie
    const incomingAuth = req.headers.get('authorization');
    const cookieToken = req.cookies.get('access_token')?.value;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (incomingAuth) {
      headers['Authorization'] = incomingAuth;
    } else if (cookieToken) {
      headers['Authorization'] = `Bearer ${cookieToken}`;
    }
    // Forward the request to FastAPI backend
    const response = await fetch(`${BACKEND_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: req.signal
    });
    
    // Check if the response is ok
    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `Backend server error: ${errorText}` },
        { status: response.status }
      );
    }
    
    // Return the response from the backend
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in backend-chat API route:', error);
    return NextResponse.json(
      { error: 'Error connecting to backend' },
      { status: 500 }
    );
  }
}