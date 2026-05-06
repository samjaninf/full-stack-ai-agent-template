import { NextRequest, NextResponse } from "next/server";
import { backendFetch, BackendApiError } from "@/lib/server-api";
import { requireAdmin } from "@/lib/admin-auth";

export async function GET(request: NextRequest) {
  try {
    const adminCheck = await requireAdmin(request);
    if ("error" in adminCheck) return adminCheck.error;
    const { accessToken } = adminCheck;

    // Forward query params to backend admin-list endpoint
    const searchParams = request.nextUrl.searchParams;
    const params = new URLSearchParams();
    const skip = searchParams.get("skip");
    const limit = searchParams.get("limit");
    const includeArchived = searchParams.get("include_archived");
    const search = searchParams.get("search");

    if (skip) params.set("skip", skip);
    if (limit) params.set("limit", limit);
    if (includeArchived) params.set("include_archived", includeArchived);
    if (search) params.set("search", search);

    const qs = params.toString();
    const url = `/api/v1/conversations/admin-list${qs ? `?${qs}` : ""}`;

    const data = await backendFetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof BackendApiError) {
      return NextResponse.json(
        { detail: error.message || "Failed to fetch conversations" },
        { status: error.status },
      );
    }
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
