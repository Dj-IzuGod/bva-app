/**
 * useDebouncedValue.js -- delays propagating a fast-changing value.
 *
 * The search box would otherwise fire one API request per keystroke. This
 * hook keeps the "draft" value the user types and only releases it after
 * they stop typing for `delayMs`.
 */

import { useEffect, useState } from "react";

export function useDebouncedValue(value, delayMs = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer); // reset the timer on every change
  }, [value, delayMs]);

  return debounced;
}
