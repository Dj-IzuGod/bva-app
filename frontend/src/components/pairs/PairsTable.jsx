/**
 * PairsTable.jsx -- the Pair Explorer table.
 *
 * Presentational: receives rows and callbacks, owns no fetching. Column
 * headers are buttons that drive server-side sorting (only fields the
 * Phase 2 API accepts are sortable). Every value shown comes straight from
 * the report row -- nothing is hardcoded.
 */

import Badge from "../ui/Badge.jsx";

/** `key` mirrors the Phase 2 API's allowed sort fields. */
const COLUMNS = [
  { key: "pair_id", label: "Pair ID", numeric: false },
  { key: "pair_type", label: "Type", numeric: false },
  { key: "vulnerability", label: "Vulnerability", numeric: false },
  { key: "distance", label: "Distance", numeric: true },
  { key: "cosine_similarity", label: "Cosine", numeric: true },
  { key: "status", label: "Status", numeric: false },
  { key: "flags", label: "Flags", numeric: false, sortable: false },
];

/** Vulnerability grade -> Badge variant (semantic colors). */
const VULN_VARIANT = { HIGH: "high", MEDIUM: "medium", LOW: "low", NONE: "none" };

/** Format a numeric report field to 4 decimals, or an em dash when missing. */
function fmtNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(4) : "—";
}

/** The pipeline writes booleans; tolerate CSV-style "True" strings too. */
function isFlagged(value) {
  return value === true || value === "True";
}

export default function PairsTable({ items, sortBy, sortOrder, onSort, onOpenPair }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={`px-4 py-3 ${col.numeric ? "text-right" : ""}`}
              >
                {col.sortable === false ? (
                  col.label
                ) : (
                  <button
                    type="button"
                    onClick={() => onSort(col.key)}
                    className="inline-flex items-center gap-1 hover:text-slate-900"
                    title={`Sort by ${col.label}`}
                  >
                    {col.label}
                    {/* Active column shows direction; inactive hint sorting. */}
                    <span aria-hidden="true">
                      {sortBy === col.key ? (sortOrder === "asc" ? "▲" : "▼") : "↕"}
                    </span>
                  </button>
                )}
              </th>
            ))}
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-100">
          {!items.length && (
            <tr>
              <td colSpan={COLUMNS.length} className="px-4 py-10 text-center text-slate-500">
                No pairs match the current filters.
              </td>
            </tr>
          )}

          {items.map((row) => {
            const vulnVariant = VULN_VARIANT[row.vulnerability] ?? "neutral";
            const flaggedFA = isFlagged(row.is_false_accept);
            const flaggedFR = isFlagged(row.is_false_reject);

            return (
              <tr
                key={row.pair_id ?? `${row.image_a}-${row.image_b}`}
                onClick={() => onOpenPair(row.pair_id)}
                tabIndex={0}
                role="link"
                onKeyDown={(event) => {
                  if (event.key === "Enter") onOpenPair(row.pair_id);
                }}
                className="cursor-pointer hover:bg-slate-50"
                title="Open pair detail"
              >
                <td className="px-4 py-2.5 font-medium text-slate-900">
                  {row.pair_id ?? "—"}
                </td>
                <td className="px-4 py-2.5">
                  {row.pair_type ? (
                    <Badge variant={row.pair_type}>{row.pair_type}</Badge>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-4 py-2.5">
                  {row.vulnerability ? (
                    <Badge variant={vulnVariant}>{row.vulnerability}</Badge>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-xs">
                  {fmtNumber(row.distance)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-xs">
                  {fmtNumber(row.cosine_similarity)}
                </td>
                <td className="px-4 py-2.5 text-slate-600">{row.status ?? "—"}</td>
                <td className="whitespace-nowrap px-4 py-2.5">
                  {flaggedFA && (
                    <span title="False accept (impostor scored below threshold)">
                      <Badge variant="impostor">FA</Badge>
                    </span>
                  )}{" "}
                  {flaggedFR && (
                    <span title="False reject (genuine scored above threshold)">
                      <Badge variant="high">FR</Badge>
                    </span>
                  )}
                  {!flaggedFA && !flaggedFR && (
                    <span className="text-slate-400">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
