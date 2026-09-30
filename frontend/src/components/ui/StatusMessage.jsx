/**
 * StatusMessage.jsx -- ONE component for loading / error / empty states so
 * every screen shows them identically (UI addendum).
 *
 * Props:
 *   state   "loading" | "error" | "empty"
 *   message human-readable detail (error/empty states)
 *   onRetry optional retry callback (error state)
 */

export default function StatusMessage({ state, message, onRetry }) {
  if (state === "loading") {
    return (
      <div className="flex items-center gap-3 py-10 text-sm text-slate-500">
        <span
          aria-hidden="true"
          className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-teal-600"
        />
        Loading...
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="rounded-[10px] border border-red-200 bg-red-50 px-5 py-4 text-sm">
        <p className="font-semibold text-red-700">Something went wrong</p>
        <p className="mt-1 text-red-600">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 rounded border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100"
          >
            Try again
          </button>
        )}
      </div>
    );
  }

  return ( // empty
    <div className="py-10 text-center text-sm text-slate-500">
      <p>No data to display.</p>
      {message && <p className="mt-1 text-slate-400">{message}</p>}
    </div>
  );
}
