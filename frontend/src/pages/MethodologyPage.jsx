/**
 * MethodologyPage.jsx -- Phase 5: plain-English methodology.
 *
 * Static prose EXCEPT the numbers: every threshold and metric is fetched
 * from GET /api/summary at mount time via the shared apiClient -- nothing
 * is hardcoded (project rule). Reuses Card / Badge / StatusMessage.
 */

import { useEffect, useState } from "react";
import Card from "../components/ui/Card.jsx";
import Badge from "../components/ui/Badge.jsx";
import StatusMessage from "../components/ui/StatusMessage.jsx";
import { apiGet } from "../services/apiClient.js";

/** Report grades (HIGH/MEDIUM/LOW/NONE) -> Badge variant keys (lowercase).
 *  Kept local like ScorePage's map; lift to a shared module if you prefer. */
const VULN_VARIANT = { HIGH: "high", MEDIUM: "medium", LOW: "low", NONE: "none" };

export default function MethodologyPage() {
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading"); // loading | ready | error

  useEffect(() => {
    apiGet("/api/summary")
      .then((d) => { setData(d); setState("ready"); })
      .catch(() => setState("error"));
  }, []);

  if (state === "loading") {
    return <StatusMessage state="loading" message="Loading run metrics…" />;
  }
  if (state === "error") {
    return (
      <StatusMessage
        state="error"
        message="Could not load run metrics -- is the API running? The explanations below are still valid."
        onRetry={() => setState("loading")}
      />
    );
  }

  const tr = data?.threshold_report ?? {};
  const th = tr.thresholds ?? {};
  const summary = data?.summary ?? {};
  const vulnCounts = summary.vulnerability_counts ?? {};

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Methodology</h1>
        <p className="mt-1 text-sm text-slate-500">
          How this framework judges a pair of faces -- in plain English.
        </p>
      </header>

      <Card title="What the framework does">
        <p className="text-sm leading-relaxed text-slate-600">
          The Biometric Vulnerability Assessment framework measures how risky a face pair is for a
          face-recognition system. Two photos go in; a number called a <strong>distance</strong> comes
          out -- small distance means the two photos look like the same person, large distance means
          they look like different people. That distance is then compared against thresholds learned
          from a real experiment (the ND-TWINS dataset: identical twins, their biological siblings,
          and unrelated people) to give every pair a <strong>vulnerability grade</strong>.
        </p>
      </Card>

      <Card title="The four pair types">
        <div className="space-y-3 text-sm leading-relaxed text-slate-600">
          <p><strong>Genuine</strong> -- two photos of the same person. These <em>should</em> be accepted by the system. If they are rejected, that is a <strong>false reject</strong>.</p>
          <p><strong>Twin</strong> -- two photos of monozygotic (identical) twins. Different people, nearly identical faces. This is the hardest case and the reason this project exists.</p>
          <p><strong>Sibling</strong> -- two photos of biological siblings (not twins). Similar, but less deceptive than twins.</p>
          <p><strong>Impostor</strong> -- two photos of unrelated people. These <em>should</em> be rejected. If accepted, that is a <strong>false accept</strong>.</p>
        </div>
      </Card>

      <Card title="From photos to a distance">
        <p className="text-sm leading-relaxed text-slate-600">
          Each photo is detected, aligned to a standard 112×112 face crop, and converted by the
          ArcFace neural network into an <strong>embedding</strong> -- think of it as a point on a
          map where similar faces land close together. The <strong>distance</strong> is simply how
          far apart the two points are (euclidean); cosine similarity is the same idea from a
          different angle. One model, one ruler -- the same code path for the batch report and the
          Live Score page.
        </p>
      </Card>

      <Card title="How grading works (thresholds from this run)">
        <p className="mb-4 text-sm leading-relaxed text-slate-600">
          The pipeline derived two operating thresholds from the experiment: the distance below
          which only 1% of impostor pairs slip through (<strong>t@FAR=0.01</strong>), and the
          same for 10% (<strong>t@FAR=0.1</strong>). Grades are assigned per pair:
        </p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
              <th className="pb-2">Grade</th>
              <th className="pb-2">Meaning (impostor-style pair)</th>
              <th className="pb-2">Distance range in this run</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            <tr>
              <td className="py-2"><Badge variant="high">HIGH</Badge></td>
              <td className="py-2">Closest matches -- a system at this operating point would most likely falsely accept this pair.</td>
              <td className="py-2 font-mono text-xs">d ≤ {th["far_0.01"]?.toFixed(4) ?? "—"}</td>
            </tr>
            <tr>
              <td className="py-2"><Badge variant="medium">MEDIUM</Badge></td>
              <td className="py-2">Suspicious zone between the two operating points.</td>
              <td className="py-2 font-mono text-xs">{th["far_0.01"]?.toFixed(4) ?? "—"} &lt; d ≤ {th["far_0.1"]?.toFixed(4) ?? "—"}</td>
            </tr>
            <tr>
              <td className="py-2"><Badge variant="low">LOW</Badge></td>
              <td className="py-2">Clearly different faces at the strict operating point.</td>
              <td className="py-2 font-mono text-xs">d &gt; {th["far_0.1"]?.toFixed(4) ?? "—"}</td>
            </tr>
            <tr>
              <td className="py-2"><Badge variant="none">NONE</Badge></td>
              <td className="py-2">Genuine pairs are graded NONE by definition -- instead they carry a false-<em>reject</em> flag if their distance is too large.</td>
              <td className="py-2">genuine pairs only</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-4 text-xs text-slate-400">
          The numbers in the last column are read from <code>results/pipeline_report.json</code> at
          page load -- they are never hardcoded.
        </p>
      </Card>

      <Card title="What this run actually measured">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">EER</p>
            <p className="text-2xl font-semibold text-slate-900">{tr.eer != null ? `${(tr.eer * 100).toFixed(2)}%` : "—"}</p>
            <p className="text-xs text-slate-400">the point where false accepts ≈ false rejects</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">False accepts</p>
            <p className="text-2xl font-semibold text-slate-900">{summary.false_accepts ?? "—"}</p>
            <p className="text-xs text-slate-400">impostor-style pairs that slipped through at t@FAR=0.01</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">False rejects</p>
            <p className="text-2xl font-semibold text-slate-900">{summary.false_rejects ?? "—"}</p>
            <p className="text-xs text-slate-400">genuine pairs wrongly kept out</p>
          </div>
        </div>

        {/* This run's grade distribution, straight from the report summary */}
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
          <span className="text-xs uppercase tracking-wide text-slate-400">Grades:</span>
          {["HIGH", "MEDIUM", "LOW", "NONE"].map((grade) => (
            <Badge key={grade} variant={VULN_VARIANT[grade]}>
              {grade}: {(vulnCounts[grade] ?? 0).toLocaleString()}
            </Badge>
          ))}
        </div>
      </Card>

      <Card title="Honest caveats">
        <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-600">
          <li>One ArcFace model (<code>glint360k_r100</code>) on 112×112 aligned crops -- different models would draw the lines differently.</li>
          <li>Thresholds were derived on <em>related</em> impostors (twins and siblings), which is a much harsher test than random strangers -- expect stricter, more conservative grades.</li>
          <li>Grades describe <strong>vulnerability</strong>, not identity: a HIGH grade means &ldquo;this pair is dangerous for the system&rdquo;, not &ldquo;these are the same person&rdquo;.</li>
          <li>A high EER on identical twins is expected -- twins are genuinely hard to tell apart, which is exactly the point of the assessment.</li>
        </ul>
      </Card>
    </div>
  );
}
