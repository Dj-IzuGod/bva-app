/**
 * RunConfigDisclosure -- collapsed-by-default panel showing the run's
 * technical configuration (e.g. {"input_mode": "prealigned"}).
 *
 * Hidden until the toggle button is clicked; the panel then drops down
 * with a smooth height animation (CSS grid-rows trick, no JS animation).
 * The value is rendered as pretty-printed JSON (the report's own format,
 * never reformatting or hardcoding it) and arrives via the `runConfig`
 * prop, read from the report at runtime. If runConfig is missing/empty,
 * the whole panel renders nothing (graceful degradation).
 *
 * Props:
 *   runConfig -- the report's run_config object (e.g. { input_mode: "prealigned" })
 */

import { useState } from "react";

export default function RunConfigDisclosure({ runConfig }) {
  const [open, setOpen] = useState(false);

  // No config in the report -> render nothing rather than an empty box.
  if (!runConfig || typeof runConfig !== "object" || Object.keys(runConfig).length === 0) {
    return null;
  }

  const panelId = "run-config-panel";

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Toggle button -- the only thing visible while collapsed */}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="text-sm font-medium text-slate-700">
          Run configuration
          <span className="ml-2 text-xs font-normal text-slate-400">
            (technical details)
          </span>
        </span>

        {/* Chevron flips upward when open */}
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* Drop-down panel: grid-rows 0fr -> 1fr animates the height smoothly.
          overflow-hidden keeps content invisible while collapsed. */}
      <div
        id={panelId}
        className={`grid overflow-hidden transition-[grid-template-rows] duration-200 ease-in-out ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="min-h-0">
          <div className="border-t border-slate-100 px-4 py-3">
            {/* Pretty-printed JSON, same view as the report's own format */}
            <pre className="overflow-x-auto rounded-lg bg-slate-50 p-3 font-mono text-xs leading-relaxed text-slate-800">
              {JSON.stringify(runConfig, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
