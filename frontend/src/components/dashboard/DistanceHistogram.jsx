/**
 * DistanceHistogram.jsx -- genuine vs impostor embedding-distance histogram.
 *
 * This is the chart that shows whether the pipeline's distances order
 * correctly: genuine pairs (teal) should peak at LOWER distances than
 * impostor pairs (rose). A dashed reference line marks the EER threshold
 * from the report.
 *
 * The component owns the full async lifecycle of its data (loading with
 * progress, error with retry, empty state) so DashboardPage stays thin.
 */

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

import Card from "../ui/Card.jsx";
import StatusMessage from "../ui/StatusMessage.jsx";
import { PAIRTYPE_COLORS } from "../../lib/chartColors.js";

export default function DistanceHistogram({
  bins,
  eerThreshold,
  isLoading,
  progress,
  error,
  onRetry,
}) {
  const hasBins = Array.isArray(bins) && bins.length > 0;

  // Sanitise the threshold once: null/undefined/"" must NOT become 0.
  const thresholdValue =
    eerThreshold === null || eerThreshold === undefined || eerThreshold === ""
      ? null
      : Number(eerThreshold);
  const threshold = Number.isFinite(thresholdValue) ? thresholdValue : null;

  // Recharts category axes can only anchor a ReferenceLine to an existing
  // category label, so we snap the line to the bin nearest the threshold.
  const thresholdLabel = useMemo(() => {
    if (threshold === null || !hasBins) return null;
    return bins.reduce((best, bin) =>
      Math.abs(Number(bin.label) - threshold) <
      Math.abs(Number(best.label) - threshold)
        ? bin
        : best
    ).label;
  }, [threshold, bins, hasBins]);

  return (
    <Card
      title="Distance distribution"
      subtitle="Embedding distance per pair (lower = more similar); dashed line = EER threshold"
    >
      {isLoading ? (
        <StatusMessage
          state="loading"
          message={
            progress?.total
              ? `Loading pair distances — ${progress.loaded.toLocaleString()} of ${Number(progress.total).toLocaleString()} rows…`
              : "Loading pair distances…"
          }
        />
      ) : error ? (
        <StatusMessage state="error" message={error.message} onRetry={onRetry} />
      ) : !hasBins ? (
        <StatusMessage
          state="empty"
          message="No scored distances in the report — every pair failed or returned no distance."
        />
      ) : (
        <div className="px-5 pb-5">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={bins} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="label"
                interval={2} // show every 3rd label to avoid crowding
                tick={{ fontSize: 11 }}
                tickLine={false}
              />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
              <Tooltip
                labelFormatter={(label, payload) =>
                  payload?.[0]?.payload?.rangeLabel ?? label
                }
                formatter={(value, name) => [Number(value).toLocaleString(), name]}
                cursor={{ fill: "rgba(148, 163, 184, 0.1)" }}
              />
              <Legend verticalAlign="top" height={28} />
              <Bar
                dataKey="genuine"
                name="Genuine pairs"
                fill={PAIRTYPE_COLORS.genuine}
              />
              <Bar
                dataKey="impostor"
                name="Impostor pairs"
                fill={PAIRTYPE_COLORS.impostor}
              />
              {thresholdLabel && (
                <ReferenceLine
                  x={thresholdLabel}
                  stroke="#0f172a"
                  strokeDasharray="4 4"
                  label={{
                    value: "EER threshold",
                    position: "insideTopRight",
                    fontSize: 11,
                  }}
                />
              )}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
