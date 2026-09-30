/**
 * DashboardPage.jsx -- Phase 1 skeleton of the Overview Dashboard.
 *
 * Phase 3 fills this page with metric cards and charts. In Phase 1 it
 * proves the two-terminal setup end to end: it fetches /api/health and
 * reports API connectivity, report-file status, and image-dir status.
 * All copy reflects live responses -- nothing is hardcoded (HARD RULE).
 */

import { useApi } from "../hooks/useApi.js";
import Card from "../components/ui/Card.jsx";
import Badge from "../components/ui/Badge.jsx";
import StatusMessage from "../components/ui/StatusMessage.jsx";

export default function DashboardPage() {
  const { data, error, isLoading, retry } = useApi("/api/health");

  if (isLoading) return <StatusMessage state="loading" />;
  if (error) return <StatusMessage state="error" message={error.message} onRetry={retry} />;

  const { report, image_dir: imageDir } = data;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Overview</h1>
        <p className="mt-1 text-sm text-slate-500">
          Stage 6 scaffolding check -- the full dashboard arrives in Phase 3.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card title="API connection">
          <p className="text-sm text-slate-600">
            Flask server is reachable and responding.
          </p>
          <div className="mt-3">
            <Badge variant="genuine">connected</Badge>
          </div>
        </Card>

        <Card title="Pipeline report" subtitle={report.path}>
          {report.found && report.parses ? (
            <>
              <p className="text-sm text-slate-600">
                Found and parsed: {report.results_count} result rows.
              </p>
              <div className="mt-3">
                <Badge variant="low">
                  input_mode: {report.run_config?.input_mode ?? "unknown"}
                </Badge>
              </div>
            </>
          ) : (
            <>
              <p className="text-sm text-red-600">{report.error}</p>
              <div className="mt-3">
                <Badge variant="high">missing</Badge>
              </div>
            </>
          )}
        </Card>

        <Card title="Dataset images" subtitle={imageDir.path ?? "not configured"}>
          <p className="text-sm text-slate-600">
            {imageDir.configured
              ? imageDir.exists
                ? "Directory is reachable."
                : "Configured path does not exist on disk."
              : imageDir.hint}
          </p>
          <div className="mt-3">
            <Badge variant={imageDir.configured && imageDir.exists ? "genuine" : imageDir.configured ? "medium" : "none"}>
              {imageDir.configured ? (imageDir.exists ? "ready" : "invalid path") : "not set"}
            </Badge>
          </div>
        </Card>
      </div>
    </div>
  );
}
