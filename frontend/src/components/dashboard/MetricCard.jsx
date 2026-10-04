/**
 * MetricCard.jsx -- one KPI tile on the dashboard.
 *
 * Wraps the shared Card (reuse rule) and adds a label / big value / hint.
 * `tone` picks the value color from the semantic palette; every tone maps
 * to a token that already exists in tailwind.config.js.
 */

import Card from "../ui/Card.jsx";

const TONE_TEXT = {
  high: "text-vuln-high",
  medium: "text-vuln-medium",
  low: "text-vuln-low",
  none: "text-vuln-none",
  neutral: "text-slate-900",
};

export default function MetricCard({ label, value, hint, tone = "neutral" }) {
  const toneClass = TONE_TEXT[tone] || TONE_TEXT.neutral;

  return (
    <Card className="p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-semibold ${toneClass}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  );
}
