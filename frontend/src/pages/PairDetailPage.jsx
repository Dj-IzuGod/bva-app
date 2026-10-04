/**
 * PairDetailPage.jsx -- Phase 4: the full record for one pair.
 *
 * Route: /pairs/:pairId. Fetches GET /api/pairs/<pair_id> and renders the
 * row's fields plus both face images served by GET /api/image. Failed pairs
 * keep their record visible and explain themselves via the error field.
 */

import { Link, useParams } from "react-router-dom";

import { useApi } from "../hooks/useApi.js";
import Card from "../components/ui/Card.jsx";
import Badge from "../components/ui/Badge.jsx";
import StatusMessage from "../components/ui/StatusMessage.jsx";
import PairImage from "../components/pairs/PairImage.jsx";

const VULN_VARIANT = { HIGH: "high", MEDIUM: "medium", LOW: "low", NONE: "none" };

/** 4-decimal formatting for scores, or an em dash when missing. */
function fmtNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(4) : "—";
}

/** The pipeline writes booleans; tolerate CSV-style "True" strings too. */
function isFlagged(value) {
  return value === true || value === "True";
}

/** Shared "back to the table" link. */
function BackLink() {
  return (
    <Link
      to="/pairs"
      className="inline-flex items-center gap-1 text-sm text-teal-700 hover:underline"
    >
      ← Back to Pair Explorer
    </Link>
  );
}

export default function PairDetailPage() {
  const { pairId } = useParams();

  const { data, error, isLoading, retry } = useApi(
    `/api/pairs/${encodeURIComponent(pairId)}`
  );

  if (isLoading) return <StatusMessage state="loading" />;

  if (error) {
    return (
      <div className="space-y-4">
        <StatusMessage state="error" message={error.message} onRetry={retry} />
        <BackLink />
      </div>
    );
  }

  const pair = data?.item;
  if (!pair) {
    return (
      <div className="space-y-4">
        <StatusMessage state="empty" message="The API returned no record for this pair." />
        <BackLink />
      </div>
    );
  }

  const vulnVariant = VULN_VARIANT[pair.vulnerability] ?? "neutral";
  const fa = isFlagged(pair.is_false_accept);
  const fr = isFlagged(pair.is_false_reject);

  return (
    <div className="space-y-4">
      <BackLink />

      {/* ---- header: identity + classification badges ---- */}
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="mr-2 text-xl font-semibold text-slate-900">
          Pair {pair.pair_id ?? pairId}
        </h1>
        {pair.pair_type && <Badge variant={pair.pair_type}>{pair.pair_type}</Badge>}
        {pair.vulnerability && <Badge variant={vulnVariant}>{pair.vulnerability}</Badge>}
        {pair.status && <Badge variant="neutral">{pair.status}</Badge>}
        {fa && <Badge variant="impostor">false accept</Badge>}
        {fr && <Badge variant="high">false reject</Badge>}
      </div>

      {pair.error && (
        <p className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-vuln-medium">
          Pipeline error for this pair: {pair.error}
        </p>
      )}

      <section className="grid gap-4 lg:grid-cols-2">
        {/* ---- face images, served from the dataset directory ---- */}
        <Card
          title="Face images"
          subtitle="Served from the dataset directory through /api/image"
        >
          <div className="flex flex-wrap justify-around gap-6 px-5 pb-5">
            <PairImage
              path={pair.image_a}
              label={`A · id ${pair.id_a ?? "—"}`}
              alt={`Face A for pair ${pair.pair_id ?? pairId}`}
            />
            <PairImage
              path={pair.image_b}
              label={`B · id ${pair.id_b ?? "—"}`}
              alt={`Face B for pair ${pair.pair_id ?? pairId}`}
            />
          </div>
        </Card>

        {/* ---- the full record ---- */}
        <Card title="Scores and record">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 px-5 pb-5 text-sm">
            <dt className="text-slate-500">Distance</dt>
            <dd className="text-right font-mono text-xs">{fmtNumber(pair.distance)}</dd>

            <dt className="text-slate-500">Cosine similarity</dt>
            <dd className="text-right font-mono text-xs">{fmtNumber(pair.cosine_similarity)}</dd>

            <dt className="text-slate-500">Subject A</dt>
            <dd className="text-right text-slate-700">{pair.id_a ?? "—"}</dd>

            <dt className="text-slate-500">Subject B</dt>
            <dd className="text-right text-slate-700">{pair.id_b ?? "—"}</dd>

            <dt className="text-slate-500">Image A</dt>
            <dd className="break-all text-right font-mono text-xs text-slate-600">
              {pair.image_a ?? "—"}
            </dd>

            <dt className="text-slate-500">Image B</dt>
            <dd className="break-all text-right font-mono text-xs text-slate-600">
              {pair.image_b ?? "—"}
            </dd>

            <dt className="text-slate-500">False accept</dt>
            <dd className="text-right">{fa ? "Yes" : "No"}</dd>

            <dt className="text-slate-500">False reject</dt>
            <dd className="text-right">{fr ? "Yes" : "No"}</dd>
          </dl>
        </Card>
      </section>
    </div>
  );
}
