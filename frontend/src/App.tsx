import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import AdminSetupPage from "./pages/AdminSetupPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import InvitePage from "./pages/InvitePage";
import InterviewPage from "./pages/InterviewPage";
import CandidateDonePage from "./pages/CandidateDonePage";
import ResultPage from "./pages/ResultPage";
import { isAdmin } from "./api/client";

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  if (!isAdmin()) {
    return <Navigate to="/admin/login" state={{ from: location.pathname }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Public admin login */}
      <Route path="/admin/login" element={<AdminLoginPage />} />

      {/* Admin-only */}
      <Route path="/" element={<RequireAdmin><AdminSetupPage /></RequireAdmin>} />
      <Route path="/admin" element={<RequireAdmin><AdminDashboardPage /></RequireAdmin>} />
      <Route path="/result/:id" element={<RequireAdmin><ResultPage /></RequireAdmin>} />

      {/* Candidate-facing (public via invite link) */}
      <Route path="/invite/:inviteId" element={<InvitePage />} />
      <Route path="/interview/:id" element={<InterviewPage />} />
      <Route path="/done/:id" element={<CandidateDonePage />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
