import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
    const data = await response.json();
    const nextRes = NextResponse.json(data, { status: response.status });
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) nextRes.headers.set('set-cookie', setCookie);
    return nextRes;
  } catch (error) {
    console.error('Error in logout proxy:', error);
    return NextResponse.json({ error: 'Error logging out' }, { status: 500 });
  }
} 