/**
 * useApi.js -- reusable data-fetching hook.
 *
 * Returns { data, error, isLoading, retry } for any GET endpoint:
 *   - isLoading drives spinner/skeleton states,
 *   - error is an ApiError (rendered by StatusMessage),
 *   - retry() refetches after a failure.
 *
 * Every page in later phases fetches through this hook so loading/empty/
 * error states stay identical across the app (UI addendum).
 */

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../services/apiClient.js";

export function useApi(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [attempt, setAttempt] = useState(0); // bump to trigger a refetch

  useEffect(() => {
    let cancelled = false; // guard against setState after unmount
    setIsLoading(true);
    setError(null);

    apiGet(path)
      .then((body) => { if (!cancelled) setData(body); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setIsLoading(false); });

    return () => { cancelled = true; };
  }, [path, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { data, error, isLoading, retry };
}
