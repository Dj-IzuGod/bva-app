/**
 * SideNav.jsx -- primary navigation. NavLink gives active-page highlighting.
 * Each later phase adds one entry here plus a route in App.jsx.
 */

import { NavLink } from "react-router-dom";

const ITEMS = [
  { to: "/", label: "Dashboard", end: true, icon: <IconGrid /> },
  { to: "/pairs", label: "Pair Explorer", icon: <IconList /> },
  { to: "/methodology", label: "Methodology", icon: <IconBook /> },
];

export default function SideNav() {
  return (
    <nav className="flex flex-col gap-1 p-3">
      <p className="px-3 pb-2 pt-1 text-xs font-semibold uppercase tracking-widest text-slate-400">
        BVA Framework
      </p>
      {ITEMS.map(({ to, label, end, icon }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded px-3 py-2 text-sm font-medium ${
              isActive ? "bg-teal-50 text-teal-800" : "text-slate-600 hover:bg-slate-100"
            }`
          }
        >
          {icon}
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

/* Small inline SVG icons -- no icon-library dependency. */
function IconGrid() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
      <path d="M3 3h6v6H3V3zm8 0h6v6h-6V3zM3 11h6v6H3v-6zm8 0h6v6h-6v-6z" />
    </svg>
  );
}

function IconList() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden="true">
      <path d="M3 5h14M3 10h14M3 15h14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function IconBook() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden="true">
      <path
        d="M5.5 2.5h9A1.5 1.5 0 0 1 16 4v13.5l-6-3-6 3V4a1.5 1.5 0 0 1 1.5-1.5z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}
