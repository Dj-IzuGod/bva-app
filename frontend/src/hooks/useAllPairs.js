/**
 * useAllPairs.js -- fetches EVERY result row for chart aggregation.
 *
 * /api/pairs is paginated (server caps page_size at 200), so the dashboard
 * walks the pages in a loop until pagination.has_next is exhausted. This
 * stays within the approved Phase 2 API -- no new endpoint needed.
 *
 * Returns { rows, error, isLoading, progress, retry }:
 *   - rows:      the combined result rows (empty until loaded)
 *   - progress:  { loaded, total } for the loading indicator
 *   - retry:     refetch after a failure
 */

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../services/apiClient.js";

const PAGE_SIZE = 200; // server-enforced maximum per request
const MAX_PAGES = 500; // safety cap (~100k rows) against runaway loops

export function useAllPairs() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [progress, setProgress] = useState({ loaded: 0, total: null });
  const [attempt, setAttempt] = useState(0); // bump to refetch

  useEffect(() => {
    let cancelled = false; // guard against setState after unmount

    setIsLoading(true);
    setError(null);
    setRows([]);
    setProgress({ loaded: 0, total: null });

    (async () => {
      try {
        const all = [];
        for (let page = 1; page <= MAX_PAGES; page += 1) {
          const payload = await apiGet(`/api/pairs?page=${page}&page_size=${PAGE_SIZE}`);
          if (cancelled) return;

          all.push(...(payload.items || []));
          const pagination = payload.pagination || {};
          setProgress({
            loaded: all.length,
            total: pagination.total_items ?? null,
          });

          const totalPages = pagination.total_pages ?? page;
          if (page >= totalPages || !(payload.items || []).length) break;
        }
        if (!cancelled) setRows(all);
      } catch (err) {
        if (!cancelled) setError(err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { rows, error, isLoading, progress, retry };
}
