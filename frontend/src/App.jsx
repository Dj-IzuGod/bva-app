/**
 * App.jsx -- route table. Layout lives in AppShell; each phase adds its
 * page here (Phase 3 fills the dashboard, Phase 4 the explorer, Phase 5
 * methodology).
 */

import { Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import PlaceholderPage from "./pages/PlaceholderPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route
          path="/pairs"
          element={<PlaceholderPage title="Pair Explorer" note="Arrives in Phase 4." />}
        />
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
