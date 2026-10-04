/**
 * PairsPage.jsx -- Phase 4: the Pair Explorer.
 *
 * A filterable, sortable, paginated table over GET /api/pairs. All filter /
 * sort / pagination state lives in the URL query string (react-router's
 * useSearchParams), so a filtered view survives refresh, is shareable, and
 * the browser back/forward buttons work.
 *
 * Search is debounced: the user types into a draft input; only after 300ms
 * of silence is the value committed to the URL, which triggers the fetch
 * through useApi's path dependency.
 *
 * Page size is also mirrored to localStorage (an allowed UI preference per
 * the storage rule) so the chosen size survives even without a URL param.
 */

import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useApi } from "../hooks/useApi.js";
import { useDebouncedValue } from "../hooks/useDebouncedValue.js";
import Card from "../components/ui/Card.jsx";
import StatusMessage from "../components/ui/StatusMessage.jsx";
import FilterBar from "../components/pairs/FilterBar.jsx";
import PairsTable from "../components/pairs/PairsTable.jsx";
import Pagination from "../components/pairs/Pagination.jsx";

/** localStorage key for the page-size preference. */
const PAGE_SIZE_KEY = "bva.pairs.pageSize";

/** Sizes offered in the dropdown; 200 is the server-side maximum. */
const PAGE_SIZES = [10, 25, 50, 100, 200];

/** Read the stored page size, ignoring anything invalid or blocked. */
function readStoredPageSize() {
  try {
    const stored = Number(localStorage.getItem(PAGE_SIZE_KEY));
    return PAGE_SIZES.includes(stored) ? stored : null;
  } catch {
    return null; // localStorage unavailable (privacy mode) -- use default
  }
}

export default function PairsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // ---- current filter/sort/page state, read from the URL ------------------
  const q = searchParams.get("q") ?? "";
  const pairType = searchParams.get("pair_type") ?? "";
  const vulnerability = searchParams.get("vulnerability") ?? "";
  const status = searchParams.get("status") ?? "";
  const sortBy = searchParams.get("sort_by") ?? "pair_id";
  const sortOrder = searchParams.get("sort_order") ?? "asc";
  const page = Number(searchParams.get("page")) || 1;
  const pageSize =
    Number(searchParams.get("page_size")) || readStoredPageSize() || 25;

  // ---- debounced search draft ----------------------------------------------
  const [searchDraft, setSearchDraft] = useState(q);
  const debouncedDraft = useDebouncedValue(searchDraft, 300);

  // Keep the draft in sync when the URL changes behind our back
  // (back/forward navigation, a pasted link).
  useEffect(() => {
    setSearchDraft(q);
  }, [q]);

  // Commit the draft to the URL once the user stops typing.
  useEffect(() => {
    if (debouncedDraft !== q) {
      updateParams({ q: debouncedDraft, page: "" }); // "" deletes page -> 1
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedDraft]);

  // ---- URL helpers ----------------------------------------------------------
  /** Merge a patch into the query string; "" or null deletes the key. */
  function updateParams(patch) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (value === "" || value === null || value === undefined) {
        next.delete(key);
      } else {
        next.set(key, String(value));
      }
    }
    setSearchParams(next);
  }

  /** Any filter change restarts the list at page 1. */
  function handleFilterChange(patch) {
    updateParams({ ...patch, page: "" });
  }

  /** Sort: same column flips direction, a new column starts ascending. */
  function handleSort(field) {
    if (field === sortBy) {
      updateParams({ sort_order: sortOrder === "asc" ? "desc" : "asc", page: "" });
    } else {
      updateParams({ sort_by: field, sort_order: "asc", page: "" });
    }
  }

  /** Page-size changes also persist as a UI preference (localStorage). */
  function handlePageSizeChange(size) {
    try {
      localStorage.setItem(PAGE_SIZE_KEY, String(size));
    } catch {
      // Preference is best-effort; the URL still carries the value.
    }
    updateParams({ page_size: size, page: "" });
  }

  /** Reset every filter and pagination parameter to the default view. */
  function handleClearFilters() {
    setSearchParams(new URLSearchParams());
  }

  // ---- data fetching ---------------------------------------------------------
  // Translate the URL state into the Phase 2 API's query parameters.
  const apiQuery = useMemo(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    if (q) params.set("search", q);
    if (pairType) params.set("pair_type", pairType);
    if (vulnerability) params.set("vulnerability", vulnerability);
    if (status) params.set("status", status);
    params.set("sort_by", sortBy);
    params.set("sort_order", sortOrder);
    return params.toString();
  }, [page, pageSize, q, pairType, vulnerability, status, sortBy, sortOrder]);

  const { data, error, isLoading, retry } = useApi(`/api/pairs?${apiQuery}`);

  const items = data?.items ?? [];
  const pagination = data?.pagination ?? null;
  const hasActiveFilters = Boolean(q || pairType || vulnerability || status);

  // ---- render -----------------------------------------------------------------
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Pair Explorer</h1>
        <p className="mt-1 text-sm text-slate-500">
          Browse, filter, and inspect individual pairs from the pipeline report.
        </p>
      </div>

      <FilterBar
        searchDraft={searchDraft}
        onSearchDraftChange={setSearchDraft}
        pairType={pairType}
        vulnerability={vulnerability}
        status={status}
        pageSize={pageSize}
        pageSizes={PAGE_SIZES}
        onChange={handleFilterChange}
        onPageSizeChange={handlePageSizeChange}
        onClear={handleClearFilters}
        hasActiveFilters={hasActiveFilters}
      />

      {error ? (
        <StatusMessage state="error" message={error.message} onRetry={retry} />
      ) : (
        <>
          {/* Dim and lock the table while a fresh page loads. Stale rows stay
              visible because useApi keeps old data until the new reply lands. */}
          <Card className={isLoading ? "pointer-events-none opacity-60" : ""}>
            <PairsTable
              items={items}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              onOpenPair={(pairId) => navigate(`/pairs/${encodeURIComponent(pairId)}`)}
            />
          </Card>

          {pagination && (
            <Pagination
              pagination={pagination}
              onPageChange={(nextPage) =>
                updateParams({ page: nextPage > 1 ? String(nextPage) : "" })
              }
            />
          )}
        </>
      )}
    </div>
  );
}
