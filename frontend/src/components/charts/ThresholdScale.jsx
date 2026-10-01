/**
 * ThresholdScale -- horizontal 0..max ruler showing WHERE a live distance
 * falls relative to the run's t@FAR thresholds. Pure divs (no chart lib).
 *
 * Zones (same palette as every vulnerability grade in the app; note the
 * direction: SMALL distance = more similar faces = riskier = HIGH):
 *   [0 .............. t@FAR=0.01]  HIGH   (red)
 *   (t@FAR=0.01 ... t@FAR=0.1]     MEDIUM (amber)
 *   (t@FAR=0.1 .......... max]     LOW    (blue)
 *
 * Props:
 *   distance   -- live euclidean distance (number)
 *   thresholds -- { "far_0.01": n, "far_0.1": n } straight from the report
 */

export default function ThresholdScale({ distance, thresholds }) {
  const t001 = thresholds?.["far_0.01"];
  const t01 = thresholds?.["far_0.1"];

  // Defensive: the report is validated upstream, but never crash the page.
  if (typeof distance !== "number" || !t001 || !t01) {
    return <p className="text-sm text-slate-400">Thresholds unavailable -- cannot plot scale.</p>;
  }

  // Domain: cover the distance AND both thresholds, with a small margin.
  const domainMax = Math.max(distance, t01, 0.9) * 1.05;
  const pct = (v) => `${(v / domainMax) * 100}%`;

  const zones = [
    { width: pct(t001), color: "bg-red-500", label: "HIGH" },            // 0 -> t@0.01
    { width: pct(t01 - t001), color: "bg-amber-400", label: "MEDIUM" },  // t@0.01 -> t@0.1
    { width: pct(domainMax - t01), color: "bg-blue-500", label: "LOW" }, // t@0.1 -> max
  ];

  return (
    <div>
      {/* Zone bar */}
      <div className="relative h-4 w-full overflow-hidden rounded-full">
        <div className="flex h-full w-full">
          {zones.map((z, i) => (
            <div key={i} className={`${z.color} h-full`} style={{ width: z.width }} />
          ))}
        </div>

        {/* Marker: the live score's position on the scale */}
        <div className="absolute top-[-4px] h-6 w-0.5 bg-slate-900" style={{ left: pct(distance) }} />
      </div>

      {/* Threshold tick labels + live score label */}
      <div className="relative mt-1 h-10 text-xs text-slate-500">
        <span className="absolute -translate-x-1/2" style={{ left: pct(t001) }}>t@FAR=0.01 · {t001.toFixed(4)}</span>
        <span className="absolute -translate-x-1/2" style={{ left: pct(t01) }}>t@FAR=0.1 · {t01.toFixed(4)}</span>
        <span className="absolute -translate-x-1/2 font-semibold text-slate-900" style={{ left: pct(distance) }}>
          your pair: {distance.toFixed(4)}
        </span>
      </div>
    </div>
  );
}
