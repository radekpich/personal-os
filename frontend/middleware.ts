import { NextResponse, type NextRequest } from "next/server";

const PRIVATE_PREFIXES = ["/dashboard", "/tasks", "/inbox", "/settings"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPrivate = PRIVATE_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
  const hasAccessCookie = request.cookies.has("access_token");
  const hasRefreshCookie = request.cookies.has("refresh_token");
  const hasSessionCookie = hasAccessCookie || hasRefreshCookie;

  if (isPrivate && !hasSessionCookie) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (pathname === "/login" && hasAccessCookie) {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = "/dashboard";
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/tasks/:path*", "/inbox/:path*", "/settings/:path*", "/login"],
};
