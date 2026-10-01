/**
 * ScorePage.jsx -- Phase 5 CORE FEATURE: live scoring.
 *
 * The user uploads two face photos; the browser POSTs them as
 * multipart/form-data to POST /api/score, which runs the REAL pipeline
 * (detect + align -> ArcFace embed -> classify) and grades the pair with
 * the exact thresholds from the validated run. Nothing shown here is
 * decided in the frontend -- every number comes from the API response,
 * which reads them from results/pipeline_report.json at request time.
 */

import { useEffect, useState } from "react";
import Card from "../components/ui/Card.jsx";
import Badge from "../components/ui/Badge.jsx";
import StatusMessage from "../components/ui/StatusMessage.jsx";
import { apiPost } from "../services/apiClient.js";
import ImageUploadTile from "../components/upload/ImageUploadTile.jsx";
import ThresholdScale from "../components/charts/ThresholdScale.jsx";

/** Report grades (HIGH/MEDIUM/LOW/NONE) -> Badge variant keys (lowercase). */
const VULN_VARIANT = { HIGH: "high", MEDIUM: "medium", LOW: "low", NONE: "none" };

/** Map a thrown ApiError to the best plain-English guidance. Server error
 *  payloads already carry friendly `message` fields (see score.py); this
 *  only adds context where the server cannot help (413's body is not JSON,
 *  and a dead network never answers). */
function friendlyError(err) {
  switch (err?.status) {
    case 0:
      return err.message;
    case 413:
      return "That upload is too large -- keep the request under 16 MB.";
    default:
      return err?.message || "Scoring failed. Check the API terminal.";
  }
}

export default function ScorePage() {
  // Each slot holds { file, url } so <img> previews can be shown.
  const [slotA, setSlotA] = useState(null);
  const [slotB, setSlotB] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Single owner of object-URL lifecycle: revoke the previous slot's URL
  // whenever the slot changes, and the current one on unmount.
  useEffect(() => () => { if (slotA) URL.revokeObjectURL(slotA.url); }, [slotA]);
  useEffect(() => () => { if (slotB) URL.revokeObjectURL(slotB.url); }, [slotB]);

  /** Wrap a picked File into { file, url } for preview + upload. */
  function makeSlot(file) {
    return { file, url: URL.createObjectURL(file) };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!slotA || !slotB || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("image_a", slotA.file);
      fd.append("image_b", slotB.file);
      fd.append("pair_type", "impostor"); // uploads have no ground truth

      // Vite dev proxy forwards /api/* to Flask (Phase 1 wiring).
      const payload = await apiPost("/api/score", fd, { asForm: true });
      setResult(payload);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Live Score</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload two face photos -- they are scored with the same ArcFace model and
          graded with the exact thresholds from the validated pipeline run.
        </p>
      </header>

      <Card title="1 · Choose two photos">
        <form onSubmit={handleSubmit} className="grid gap-6 sm:grid-cols-2">
          <ImageUploadTile
            label="Image A"
            file={slotA?.file}
            previewUrl={slotA?.url}
            disabled={loading}
            onSelect={(f) => setSlotA(makeSlot(f))}
            onClear={() => setSlotA(null)}
          />
          <ImageUploadTile
            label="Image B"
            file={slotB?.file}
            previewUrl={slotB?.url}
            disabled={loading}
            onSelect={(f) => setSlotB(makeSlot(f))}
            onClear={() => setSlotB(null)}
          />

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={!slotA || !slotB || loading}
              className="rounded-lg bg-teal-700 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? "Scoring…" : "Score pair"}
            </button>
            {loading && (
              <p className="mt-2 text-xs text-slate-500">
                The first request loads the dlib + ArcFace models and can take up to a minute.
                Later requests are much faster.
              </p>
            )}
          </div>
        </form>
      </Card>

      {/* ---- Loading / error states (your StatusMessage contract: state=) ---- */}
      {loading && (
        <StatusMessage state="loading" message="Running detect → align → embed → classify…" />
      )}
      {error && <StatusMessage state="error" message={error} />}

      {/* ---- Result panel ---- */}
      {result && (
        <Card title="2 · Result">
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm text-slate-500">Vulnerability grade:</span>
              <Badge variant={VULN_VARIANT[result.vulnerability] ?? "neutral"}>
                {result.vulnerability}
              </Badge>
              {result.is_false_accept && <Badge variant="high">would be falsely accepted</Badge>}
              {result.is_false_reject && <Badge variant="none">would be falsely rejected</Badge>}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-400">Euclidean distance</p>
                <p className="text-3xl font-semibold text-slate-900">
                  {result.distance?.toFixed(4)}
                </p>
                <p className="text-xs text-slate-400">lower = more similar faces</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-400">Cosine similarity</p>
                <p className="text-3xl font-semibold text-slate-900">
                  {result.cosine_similarity?.toFixed(4)}
                </p>
                <p className="text-xs text-slate-400">higher = more similar faces</p>
              </div>
            </div>

            <div>
              <h3 className="mb-2 text-sm font-medium text-slate-600">Where your pair falls</h3>
              <ThresholdScale distance={result.distance} thresholds={result.thresholds_used} />
            </div>

            <p className="text-xs text-slate-400">
              Graded as an &ldquo;{result.pair_type_assumed}&rdquo; pair using thresholds from the
              validated run (EER {result.thresholds_used?.eer?.toFixed(4)}).
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
