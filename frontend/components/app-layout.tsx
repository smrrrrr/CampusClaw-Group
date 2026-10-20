"use client";

import type { ReactNode } from "react";

export interface NavItem {
  key: string;
  label: string;
  icon: string;
  to?: string;
  children?: NavItem[];
  /** 分组标题：相同值合并为一组，变化时输出分隔标题 */
  section?: string;
  description?: string;
  expanded?: boolean;
  accessory?: ReactNode;
}

const ICONS: Record<string, ReactNode> = {
  home: <path d="M3 10.5 12 3l9 7.5M5 9v11h5v-6h4v6h5V9" fill="none" stroke="currentColor" strokeWidth={1.8} />,
  doc: <path d="M7 3h7l4 4v14H7zM14 3v4h4" fill="none" stroke="currentColor" strokeWidth={1.8} />,
  robot: (
    <g fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
      <rect x="5" y="7" width="14" height="13" rx="3" />
      <path d="M12 7V4" />
      <path d="M9 11h.01M15 11h.01M9.5 16a3.5 3.5 0 0 0 5 0" />
    </g>
  ),
  chat: <path d="M4 4h16v12H8l-4 4V4z" fill="none" stroke="currentColor" strokeWidth={1.8} />,
  upload: <path d="M12 16V4m0 0-4 4m4-4 4 4M5 20h14" fill="none" stroke="currentColor" strokeWidth={1.8} />,
  log: <path d="M4 20V10m5 10V4m5 16v-7m5 7V7" fill="none" stroke="currentColor" strokeWidth={1.8} />,
  tools: (
    <path
      d="M14.7 6.3c1-.3 1.6-.8 2.1-1.5l-2.1-2.1C14 3.2 13.5 3.8 13.2 4.8M21 12c0 3.3-2.7 6-6 6H9c-3.3 0-6-2.7-6-6s2.7-6 6-6h6c.9 0 1.7.2 2.4.6M10 10.5h.01M14 13.5h.01"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
    />
  ),
  audit: <path d="M4 20V10m5 10V4m5 16v-7m5 7V7" fill="none" stroke="currentColor" strokeWidth={1.8} />,
  students: <g fill="none" stroke="currentColor" strokeWidth={1.8}><circle cx="9" cy="7" r="3" /><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 5v2" /></g>,
  books: <g fill="none" stroke="currentColor" strokeWidth={1.8}><path d="M3 4h5v16H3zM8 6h5v14H8zM15 4l5-1 3 16-5 1z" /></g>,
  edit: <path d="m4 16-1 5 5-1L21 7l-4-4L4 16ZM14 6l4 4" fill="none" stroke="currentColor" strokeWidth={1.8} />,
  search: <g fill="none" stroke="currentColor" strokeWidth={1.8}><circle cx="10" cy="10" r="7" /><path d="m15 15 6 6" /></g>,
  assignment: <g fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round"><path d="M7 4h10a2 2 0 0 1 2 2v15H5V6a2 2 0 0 1 2-2Z" /><path d="M9 4V2h6v2M8 10h8M8 14h8M8 18h5" /></g>,
  mistake: <g fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"><path d="M12 4v9" /><circle cx="12" cy="18" r="1" /></g>,
  analysis: <g fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinejoin="round"><path d="M3 20h18M5 17V9h3v8M11 17V4h3v13M17 17v-5h3v5" /><path d="m5 7 5-3 4 2 5-4" /></g>,
};

function isParentActive(item: NavItem, active: string): boolean {
  if (item.key === active) return true;
  return !!item.children?.some((c) => c.key === active);
}

export function AppShell({
  brandMark = "C",
  subtitle,
  navItems,
  active,
  onNavigate,
  headerLeft,
  headerRight,
  navFoot = "演示项目 · 数据均为 mock",
  navHeader,
  children,
}: {
  brandMark?: string;
  subtitle: string;
  navItems: NavItem[];
  active: string;
  onNavigate: (key: string) => void;
  headerLeft?: ReactNode;
  headerRight?: ReactNode;
  navFoot?: ReactNode;
  navHeader?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-brand">
          <div className="b-mark">{brandMark}</div>
          <h1>CampusClaw</h1>
          <p>{subtitle}</p>
        </div>
        <nav className="app-nav" aria-label="主导航">
          {navHeader}
          {!navItems.some((item) => item.section) && <div className="sec">导航</div>}
          {navItems.map((it, idx) => {
            const parentActive = isParentActive(it, active);
            const prevSection = idx > 0 ? navItems[idx - 1].section : undefined;
            const showSection = it.section && it.section !== prevSection;
            return (
              <div key={it.key} className="nav-group">
                {showSection && <div className="sec">{it.section}</div>}
                <button
                  className={`nav-item${parentActive ? " active" : ""}`}
                  onClick={() => onNavigate(it.key)}
                  aria-current={active === it.key ? "page" : undefined}
                  title={it.description}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[it.icon] ?? ICONS.doc}</svg>
                  <span>{it.label}</span>
                </button>
                {it.accessory}
                {it.children && (parentActive || it.expanded) && (
                  <div className="nav-sub">
                    {it.children.map((c) => (
                      <button
                        key={c.key}
                        className={`nav-item sub${active === c.key ? " active" : ""}`}
                        onClick={() => onNavigate(c.key)}
                        aria-current={active === c.key ? "page" : undefined}
                        title={c.description}
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[c.icon] ?? ICONS.doc}</svg>
                        <span>{c.label}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
        <div className="footer">{navFoot}</div>
      </aside>
      <div className="app-main">
        <header className="app-headerbar">
          <div className="hdr-left">{headerLeft ?? <span className="status-dot" />}</div>
          <div className="hdr-right">{headerRight}</div>
        </header>
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
