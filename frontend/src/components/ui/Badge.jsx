/**
 * Badge.jsx -- status/grade chip using the app's fixed semantic colors
 * (vuln.* / pairtype.* from tailwind.config.js). Used for vulnerability
 * grades, pair types, and statuses on every screen.
 */

const VARIANTS = {
  high: "border-red-200 bg-red-50 text-vuln-high",
  medium: "border-amber-200 bg-amber-50 text-vuln-medium",
  low: "border-blue-200 bg-blue-50 text-vuln-low",
  none: "border-slate-200 bg-slate-100 text-vuln-none",
  genuine: "border-teal-200 bg-teal-50 text-pairtype-genuine",
  impostor: "border-rose-200 bg-rose-50 text-pairtype-impostor",
  neutral: "border-slate-200 bg-slate-100 text-slate-600",
};

export default function Badge({ variant = "neutral", children }) {
  const classes = VARIANTS[variant] || VARIANTS.neutral;
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${classes}`}
    >
      {children}
    </span>
  );
}
