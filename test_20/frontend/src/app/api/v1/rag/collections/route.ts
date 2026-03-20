import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";

// GET /api/v1/rag/collections - List collections
export async function GET(request: NextRequest) {
  try {
    const headers: Record<string, string> = {};
    const accessToken = request.cookies.get("access_token")?.value;
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }

    const data = await backendFetch("/api/v1/rag/collections", { headers });
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to fetch collections" },
        { status: error.status }
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

// POST /api/v1/rag/collections - Create collection
export async function POST(request: NextRequest) {
  const authEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";
  let accessToken: string | undefined;

  if (authEnabled) {
    accessToken = request.cookies.get("access_token")?.value;
    if (!accessToken) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }
  }

  try {
    const body = await request.json();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }

    const data = await backendFetch("/api/v1/rag/collections", {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to create collection" },
        { status: error.status }
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
