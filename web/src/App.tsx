import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { AnalyzePage } from './pages/Analyze'
import { AuditPage } from './pages/Audit'
import { ScorePage } from './pages/Score'
import { HistoryPage } from './pages/History'
import { MigratePage } from './pages/Migrate'
import { RecommendationsPage } from './pages/Recommendations'
import { DiffPage } from './pages/Diff'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/score" element={<ScorePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/migrate" element={<MigratePage />} />
        <Route path="/diff" element={<DiffPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
      </Routes>
    </Layout>
  )
}
