/**
 * AppShell.jsx -- page chrome: fixed sidebar on desktop (md+), stacked
 * brand + nav bar on small screens, and a centered content column. Pages
 * render inside <Outlet /> so only page components change per route.
 */

import { Outlet } from "react-router-dom";
import SideNav from "./SideNav.jsx";

export default function AppShell() {
  return (
    <div className="min-h-screen md:flex">
      {/* Desktop sidebar */}
      <aside className="hidden border-r border-slate-200 bg-white md:block md:w-60 md:shrink-0">
        <Brand />
        <SideNav />
      </aside>

      {/* Mobile brand + nav */}
      <div className="md:hidden">
        <div className="border-b border-slate-200 bg-white">
          <Brand />
        </div>
        <div className="border-b border-slate-200 bg-white">
          <SideNav />
        </div>
      </div>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2 px-5 py-4">
      <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-teal-600" />
      <span className="text-sm font-bold tracking-tight text-slate-900">
        Biometric Vulnerability Assessment
      </span>
    </div>
  );
}
