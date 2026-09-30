/**
 * App.jsx -- route table. Layout lives in AppShell; each phase adds its
 * page here (Phase 3 dashboard, Phase 4 pair explorer, Phase 5 methodology).
 */

import { Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import PairsPage from "./pages/PairsPage.jsx";
import PairDetailPage from "./pages/PairDetailPage.jsx";
import PlaceholderPage from "./pages/PlaceholderPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="/pairs" element={<PairsPage />} />
        <Route path="/pairs/:pairId" element={<PairDetailPage />} />
        <Route
          path="/methodology"
          element={<PlaceholderPage title="Methodology" note="Arrives in Phase 5." />}
        />
        <Route
          path="*"
          element={<PlaceholderPage title="Page not found" note="Check the address." />}
        />
      </Route>
    </Routes>
  );
}
