import { type NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const hasSession = request.cookies.getAll().some((cookie) => {
    return cookie.name.startsWith("sb-") && cookie.name.endsWith("-auth-token");
  });

  if (!hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*", "/favorites/:path*", "/subscriptions/:path*"],
};
