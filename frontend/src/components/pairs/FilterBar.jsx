/**
 * FilterBar.jsx -- search box, dropdown filters, and page-size selector.
 *
 * Presentational: all values and handlers come from PairsPage, which owns
 * the URL state. The search box edits the *draft* value; PairsPage debounces
 * it before committing to the URL and the API.
 */

const PAIR_TYPE_OPTIONS = [
  { value: "genuine", label: "Genuine" },
  { value: "impostor", label: "Impostor" },
];

/** Grades follow the fixed semantic colors (HIGH red ... NONE gray). */
const VULNERABILITY_OPTIONS = ["HIGH", "MEDIUM", "LOW", "NONE"];

// Statuses written by the pipeline. A status filter that matches nothing is
// harmless -- it just yields an empty page.
const STATUS_OPTIONS = ["success", "no_face_detected", "missing_embedding", "error"];

const inputClasses =
  "rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600";

export default function FilterBar({
  searchDraft,
  onSearchDraftChange,
  pairType,
  vulnerability,
  status,
  pageSize,
  pageSizes,
  onChange,
  onPageSizeChange,
  onClear,
  hasActiveFilters,
}) {
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-[10px] border border-slate-200 bg-white p-4 shadow-card">
      {/* Server-side search across pair_id, id_a, id_b, image_a, image_b. */}
      <div className="min-w-[220px] flex-1">
        <label htmlFor="pair-search" className="mb-1 block text-xs font-medium text-slate-600">
          Search
        </label>
        <input
          id="pair-search"
          type="search"
          value={searchDraft}
          onChange={(event) => onSearchDraftChange(event.target.value)}
          placeholder="pair ID, subject ID, or image filename…"
          className={`w-full ${inputClasses}`}
        />
      </div>

      <div>
        <label htmlFor="filter-pair-type" className="mb-1 block text-xs font-medium text-slate-600">
          Pair type
        </label>
        <select
          id="filter-pair-type"
          value={pairType}
          onChange={(event) => onChange({ pair_type: event.target.value })}
          className={inputClasses}
        >
          <option value="">All</option>
          {PAIR_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-vulnerability" className="mb-1 block text-xs font-medium text-slate-600">
          Vulnerability
        </label>
        <select
          id="filter-vulnerability"
          value={vulnerability}
          onChange={(event) => onChange({ vulnerability: event.target.value })}
          className={inputClasses}
        >
          <option value="">All</option>
          {VULNERABILITY_OPTIONS.map((grade) => (
            <option key={grade} value={grade}>{grade}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-status" className="mb-1 block text-xs font-medium text-slate-600">
          Status
        </label>
        <select
          id="filter-status"
          value={status}
          onChange={(event) => onChange({ status: event.target.value })}
          className={inputClasses}
        >
          <option value="">All</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-page-size" className="mb-1 block text-xs font-medium text-slate-600">
          Rows per page
        </label>
        <select
          id="filter-page-size"
          value={pageSize}
          onChange={(event) => onPageSizeChange(Number(event.target.value))}
          className={inputClasses}
        >
          {pageSizes.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </div>

      {hasActiveFilters && (
        <button
          type="button"
          onClick={onClear}
          className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
