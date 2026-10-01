/**
 * App.jsx -- route table. Layout lives in AppShell; pages added per phase
 * (Phase 3 dashboard, Phase 4 pair explorer, Phase 5 live score + methodology).
 */

import { Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import PairsPage from "./pages/PairsPage.jsx";
import PairDetailPage from "./pages/PairDetailPage.jsx";
import ScorePage from "./pages/ScorePage.jsx";
import MethodologyPage from "./pages/MethodologyPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="/pairs" element={<PairsPage />} />
        <Route path="/pairs/:pairId" element={<PairDetailPage />} />
        <Route path="/score" element={<ScorePage />} />
        <Route path="/methodology" element={<MethodologyPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
