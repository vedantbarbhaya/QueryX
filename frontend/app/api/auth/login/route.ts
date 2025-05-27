import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    // Read form-encoded body
    const body = await req.text();
    // Forward login to backend, include credentials for cookies
    const response = await fetch(`${BACKEND_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
      credentials: 'include',
    });
    const data = await response.json();
    // Build Next.js response and forward Set-Cookie header if present
    const nextRes = NextResponse.json(data, { status: response.status });
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) nextRes.headers.set('set-cookie', setCookie);
    return nextRes;
  } catch (error) {
    console.error('Error in login proxy:', error);
    return NextResponse.json({ error: 'Error logging in' }, { status: 500 });
  }
} 