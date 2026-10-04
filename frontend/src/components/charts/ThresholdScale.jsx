/**
 * ThresholdScale -- horizontal ruler showing WHERE a live distance falls
 * relative to the run's t@FAR thresholds. Pure divs (no chart lib).
 *
 * Zones (same palette as every vulnerability grade in the app; note the
 * direction: SMALL distance = more similar faces = riskier = HIGH):
 *   [0 .............. t@FAR=0.01]  HIGH   (red)
 *   (t@FAR=0.01 ... t@FAR=0.1]     MEDIUM (amber)
 *   (t@FAR=0.1 .......... max]     LOW    (blue)
 *
 * The interpretation paragraph below the scale is DYNAMIC: the zone name
 * and explanation are derived from the pair's distance at render time,
 * using the same comparisons as the Stage 4 classifier. (An earlier
 * version hardcoded "LOW" in that sentence -- precisely the class of bug
 * the project's "never hardcode metrics" rule exists to prevent.)
 *
 * Labels sit on three staggered rows so close thresholds never collide,
 * and the "your pair" label anchors from its right edge when the score
 * lands near the right side of the scale (so it never wraps or clips).
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
  // String form for inline styles...
  const pct = (v) => `${(v / domainMax) * 100}%`;
  // ...and numeric form for edge-awareness checks.
  const toPctNum = (v) => (v / domainMax) * 100;

  const zones = [
    { width: pct(t001), color: "bg-red-500", label: "HIGH" },            // 0 -> t@0.01
    { width: pct(t01 - t001), color: "bg-amber-400", label: "MEDIUM" },  // t@0.01 -> t@0.1
    { width: pct(domainMax - t01), color: "bg-blue-500", label: "LOW" }, // t@0.1 -> max
  ];

  // ---- Dynamic interpretation --------------------------------------------
  // Same zone logic the classifier applies (smaller distance = more
  // similar faces = riskier). One source of truth drives the marker's
  // zone, so this sentence can never disagree with the bar or the badge.
  const zoneInfo =
    distance <= t001
      ? {
          name: "HIGH",
          text:
            "This pair falls in the HIGH zone: the two faces are similar enough that a system " +
            "operating at these thresholds would likely accept them as the same person. If the " +
            "pair are actually different people, this is precisely the false-accept risk the " +
            "framework measures.",
        }
      : distance <= t01
        ? {
            name: "MEDIUM",
            text:
              "This pair falls in the MEDIUM zone: the similarity sits between the two operating " +
              "points, so the accept/reject decision would flip depending on how strict the " +
              "system's threshold is. This is the intermediate-risk band.",
          }
        : {
            name: "LOW",
            text:
              "This pair falls in the LOW zone, meaning the system sees the two images as less " +
              "likely to be falsely accepted as the same person at these thresholds.",
          };

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

      {/* Labels staggered on separate rows so close thresholds never collide */}
      <div className="relative mt-1 h-14 text-xs text-slate-500">
        <span className="absolute top-0 -translate-x-1/2 whitespace-nowrap" style={{ left: pct(t001) }}>
          t@FAR=0.01 · {t001.toFixed(4)}
        </span>
        <span className="absolute top-5 -translate-x-1/2 whitespace-nowrap" style={{ left: pct(t01) }}>
          t@FAR=0.1 · {t01.toFixed(4)}
        </span>
        <span
          className={[
            "absolute top-10 whitespace-nowrap font-semibold text-slate-900",
            // Near the right edge, anchor from the label's right side so it
            // stays inside the card instead of wrapping/clipping.
            toPctNum(distance) > 88 ? "-translate-x-full" : "-translate-x-1/2",
          ].join(" ")}
          style={{ left: pct(distance) }}
        >
          your pair: {distance.toFixed(4)}
        </span>
      </div>

      {/* Color legend (static on purpose: it describes what each colour MEANS,
          not where this particular pair falls) */}
      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-600">
        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-red-500" />
          <span>
            <strong className="text-slate-800">HIGH</strong> — high false-accept risk
          </span>
        </span>

        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-amber-400" />
          <span>
            <strong className="text-slate-800">MEDIUM</strong> — intermediate risk
          </span>
        </span>

        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-blue-500" />
          <span>
            <strong className="text-slate-800">LOW</strong> — lower false-accept risk
          </span>
        </span>
      </div>

      {/* Dynamic interpretation -- the zone name and explanation are derived
          from the pair's distance against the report thresholds, so the text
          always matches the marker's position and the grade badge above. */}
      <p className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-600">
        The colored zones show vulnerability to false acceptance. Smaller distances
        indicate greater facial similarity. {zoneInfo.text} This is not proof of identity.
      </p>
    </div>
  );
}
