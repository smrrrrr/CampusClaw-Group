import { NextRequest, NextResponse } from "next/server";

/**
 * 页面启动阶段不根据共享的辅助 Cookie 拒绝导航。
 * Access Token 只在当前标签页内存中；其他标签页可能改写 cc_role/cc_has_token。
 * AuthGate 恢复本页会话并核对路径角色后才挂载业务内容，后端继续逐接口鉴权。
 */
export function middleware(_req: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
