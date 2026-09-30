/**
 * PlaceholderPage.jsx -- temporary stand-in for pages delivered in later
 * phases (Pair Explorer = Phase 4, Methodology = Phase 5). Prevents dead
 * nav links in Phase 1 without building those pages early.
 */

export default function PlaceholderPage({ title, note }) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
      <div className="rounded-[10px] border border-dashed border-slate-300 bg-white px-5 py-12 text-center">
        <p className="text-sm font-medium text-slate-600">{note}</p>
      </div>
    </div>
  );
}
