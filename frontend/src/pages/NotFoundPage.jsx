/** NotFoundPage.jsx -- final-polish 404 for any unmatched route. */

import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 p-6 text-center">
      <p className="text-5xl font-semibold text-slate-900">404</p>
      <p className="text-sm text-slate-500">That page does not exist.</p>
      <Link
        to="/"
        className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
      >
        Back to the dashboard
      </Link>
    </div>
  );
}
