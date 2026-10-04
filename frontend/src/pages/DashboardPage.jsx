/**
 * DashboardPage.jsx -- Phase 3: the Overview dashboard.
 *
 * Data sources (everything read at runtime -- HARD RULE, nothing hardcoded):
 *   GET /api/health -> status strip: API reachability, report row count,
 *                      whether the image directory is configured
 *   GET /api/summary -> run info, thresholds, vulnerability counts, FA/FR
 *   GET /api/pairs   -> every row via useAllPairs, for the histogram and
 *                       client-side median distances
 *
 * Failure isolation: if /api/summary fails the whole page shows an error
 * (nothing can render without it), but if only the row fetch fails, the
 * metric cards stay visible and just the histogram card shows the error.
 */

import { useMemo } from "react";

import { useApi } from "../hooks/useApi.js";
import { useAllPairs } from "../hooks/useAllPairs.js";
import { computeDistanceHistogram, medianOf } from "../lib/stats.js";

import Card from "../components/ui/Card.jsx";
import Badge from "../components/ui/Badge.jsx";
import StatusMessage from "../components/ui/StatusMessage.jsx";
import MetricCard from "../components/dashboard/MetricCard.jsx";
import VulnerabilityBreakdown from "../components/dashboard/VulnerabilityBreakdown.jsx";
import DistanceHistogram from "../components/dashboard/DistanceHistogram.jsx";
import RunConfigDisclosure from "../components/ui/RunConfigDisclosure.jsx";


/** Render any missing report value as an em dash instead of "undefined". */
const fmt = (value) =>
  value === null || value === undefined || value === "" ? "—" : value;

/** Format a report number as a fixed 4-decimal distance, or an em dash. */
const fmtDistance = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(4) : "—";
};

/** Format a count with thousands separators, or an em dash. */
const fmtCount = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString() : "—";
};

export default function DashboardPage() {
  const summary = useApi("/api/summary");
  const health = useApi("/api/health");
  const pairs = useAllPairs();

  const summaryData = summary.data;
  const runSummary = summaryData?.summary ?? {};
  const thresholds = summaryData?.threshold_report ?? null;
  const counts = runSummary?.vulnerability_counts ?? null;
  const modifiedAt = summaryData?.report?.modified_at;

  // Client-side medians from the full row set. With the validated run these
  // land at ~0.824 genuine / ~0.882 impostor -- computed here at runtime,
  // never stored or hardcoded.
  const medians = useMemo(() => {
    const genuine = [];
    const impostor = [];
    for (const row of pairs.rows) {
      const d = Number(row.distance);
      if (!Number.isFinite(d)) continue;
      (row.pair_type === "genuine" ? genuine : impostor).push(d);
    }
    return { genuine: medianOf(genuine), impostor: medianOf(impostor) };
  }, [pairs.rows]);

  const bins = useMemo(
    () => computeDistanceHistogram(pairs.rows, 25),
    [pairs.rows]
  );

  // Prefer the report's own FA/FR totals; fall back to counting rows
  // client-side when the summary omits them (JSON booleans or CSV-style
  // "True"/"False" strings are both accepted).
  const falseAccepts =
    runSummary?.false_accepts ??
    pairs.rows.filter(
      (r) => r.is_false_accept === true || r.is_false_accept === "True"
    ).length;
  const falseRejects =
    runSummary?.false_rejects ??
    pairs.rows.filter(
      (r) => r.is_false_reject === true || r.is_false_reject === "True"
    ).length;

  // EER as a number, guarded, for the percentage subtext.
  const eer = Number(thresholds?.eer);
  const orderingOk =
    Number.isFinite(medians.genuine) &&
    Number.isFinite(medians.impostor) &&
    medians.genuine < medians.impostor;

  // ---- global states: nothing can render without the summary -------------
  if (summary.isLoading) return <StatusMessage state="loading" />;
  if (summary.error) {
    return (
      <StatusMessage
        state="error"
        message={summary.error.message}
        onRetry={summary.retry}
      />
    );
  }

  const hasThresholds =
    thresholds && (thresholds.eer !== undefined || thresholds.eer_threshold !== undefined);

  return (
    <div className="space-y-6">
      {/* ---- header + system status strip ---- */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Overview</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <Badge variant="neutral">{fmt(summaryData?.run_config?.input_mode)}</Badge>
            <span>
              {fmtCount(runSummary?.total)} pairs
              ({fmtCount(runSummary?.successful)} successful,{" "}
              {fmtCount(runSummary?.failed)} failed)
            </span>
            {modifiedAt && (
              <span className="text-slate-400">
                · report updated {new Date(modifiedAt).toLocaleString()}
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={health.error ? "impostor" : health.isLoading ? "neutral" : "none"}>
            {health.isLoading
              ? "API: checking…"
              : health.error
                ? "API: down"
                : "API: connected"}
          </Badge>
          <Badge variant="neutral">
            Report rows: {fmtCount(health.data?.report?.results_count)}
          </Badge>
          <Badge variant={health.data?.image_dir ? "none" : "neutral"}>
            Images: {health.data?.image_dir ? "directory set" : "not set"}
          </Badge>
        </div>
      </div>

      {/* ---- decision thresholds ---- */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-900">Decision thresholds</h2>
        {hasThresholds ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              label="EER"
              value={fmtDistance(thresholds.eer)}
              hint={
                Number.isFinite(eer) ? `Equal error rate ≈ ${(eer * 100).toFixed(1)}%` : undefined
              }
            />
            <MetricCard
              label="EER threshold"
              value={fmtDistance(thresholds.eer_threshold)}
              hint="Distance where FAR = FRR"
            />
            <MetricCard
              label="Threshold @ FAR 0.01"
              value={fmtDistance(thresholds?.thresholds?.["far_0.01"])}
              hint="1% impostor accept rate"
            />
            <MetricCard
              label="Threshold @ FAR 0.1"
              value={fmtDistance(thresholds?.thresholds?.["far_0.1"])}
              hint="10% impostor accept rate"
            />
          </div>
        ) : (
          <StatusMessage
            state="empty"
            message="Thresholds were not derived for this run — the pipeline needs at least one scored genuine and one scored impostor pair. Run the pipeline on the full dataset to populate these cards."
          />
        )}
      </section>

      {/* ---- outcomes ---- */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-900">
          Outcomes at the operating threshold
        </h2>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard
            label="False accepts"
            value={fmtCount(falseAccepts)}
            hint="Impostor pairs scored below the threshold"
            tone={Number(falseAccepts) > 0 ? "high" : "none"}
          />
          <MetricCard
            label="False rejects"
            value={fmtCount(falseRejects)}
            hint="Genuine pairs scored above the threshold"
            tone={Number(falseRejects) > 0 ? "high" : "none"}
          />
          <MetricCard
            label="Genuine median distance"
            value={pairs.isLoading ? "…" : fmtDistance(medians.genuine)}
            hint="Client-computed from all report rows"
          />
          <MetricCard
            label="Impostor median distance"
            value={pairs.isLoading ? "…" : fmtDistance(medians.impostor)}
            hint={
              pairs.isLoading
                ? "Client-computed from all report rows"
                : orderingOk
                  ? "Correctly above the genuine median"
                  : "WARNING: ordering inverted vs genuine median"
            }
          />
        </div>
      </section>

      {/* ---- per-run configuration detail (collapsed until clicked) ---- */}
      {/* NOTE: pass the API payload (summaryData), not the useApi wrapper.
          `summary` is { data, isLoading, error, retry } and has no run_config. */}
      <RunConfigDisclosure runConfig={summaryData?.run_config} />
    </div>
  );
}
