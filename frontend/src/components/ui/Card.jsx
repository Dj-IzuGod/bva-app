/**
 * Card.jsx -- base surface for every panel in the app (UI addendum:
 * card-based layout, soft shadow, 10px radius). Reused everywhere; panels
 * are never re-styled by hand.
 */

export default function Card({ title, subtitle, children, className = "" }) {
  return (
    <section
      className={`rounded-[10px] border border-slate-200 bg-white shadow-card ${className}`}
    >
      {(title || subtitle) && (
        <header className="border-b border-slate-100 px-5 py-4">
          {title && <h2 className="text-sm font-semibold text-slate-900">{title}</h2>}
          {subtitle && <p className="mt-0.5 break-all text-xs text-slate-500">{subtitle}</p>}
        </header>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}
