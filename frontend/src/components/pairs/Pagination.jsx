/**
 * Pagination.jsx -- server-driven pagination controls.
 *
 * The Phase 2 API owns filtering/sorting/pagination; this component only
 * renders the `pagination` object from the /api/pairs response and reports
 * page changes upward.
 */

export default function Pagination({ pagination, onPageChange }) {
  const {
    page,
    page_size: pageSize,
    total_items: totalItems,
    total_pages: totalPages,
    has_previous: hasPrev,
    has_next: hasNext,
  } = pagination;

  const firstRow = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastRow = Math.min(page * pageSize, totalItems);

  const buttonBase =
    "rounded border px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40";
  const enabled = "border-slate-300 bg-white text-slate-700 hover:bg-slate-50";

  return (
    <nav
      className="flex flex-wrap items-center justify-between gap-3"
      aria-label="Table pagination"
    >
      <p className="text-sm text-slate-500">
        Showing{" "}
        <span className="font-medium text-slate-700">
          {firstRow.toLocaleString()}–{lastRow.toLocaleString()}
        </span>{" "}
        of{" "}
        <span className="font-medium text-slate-700">
          {totalItems.toLocaleString()}
        </span>{" "}
        pairs
      </p>

      <div className="flex items-center gap-2">
        <button type="button" className={`${buttonBase} ${enabled}`}
          onClick={() => onPageChange(1)} disabled={!hasPrev}>
          First
        </button>
        <button type="button" className={`${buttonBase} ${enabled}`}
          onClick={() => onPageChange(page - 1)} disabled={!hasPrev}>
          Previous
        </button>
        <span className="px-2 text-sm text-slate-600">
          Page {page.toLocaleString()} of {totalPages.toLocaleString()}
        </span>
        <button type="button" className={`${buttonBase} ${enabled}`}
          onClick={() => onPageChange(page + 1)} disabled={!hasNext}>
          Next
        </button>
        <button type="button" className={`${buttonBase} ${enabled}`}
          onClick={() => onPageChange(totalPages)} disabled={!hasNext}>
          Last
        </button>
      </div>
    </nav>
  );
}
