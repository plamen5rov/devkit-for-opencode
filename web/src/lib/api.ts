import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface AnalyzeResult {
  config_path: string
  timestamp: string
  orchestrator: Record<string, any>
  audit: Record<string, any>
  optimization: Record<string, any>
  raw_analyses: Record<string, any>
}

export interface AuditResult {
  config_path: string
  findings: Array<{
    severity: string
    category: string
    title: string
    description: string
    location: string
    remediation: string
  }>
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  info_count: number
  risk_score: number
  total_findings: number
}

export interface ScoreResult {
  health_score: number
  summary: Record<string, any>
  breakdown?: Record<string, any>
}

export interface HistoryRecord {
  id: number
  timestamp: string
  config_path: string
  health_score: number
  risk_score: number
  issue_count: number
  warning_count: number
  mcp_token_estimate: number
  findings: Array<Record<string, any>>
  recommendations: Array<Record<string, any>>
}

export interface TrendData {
  timestamp: string
  health_score: number
  risk_score: number
}

export interface MigrationResult {
  config_path: string
  source_version: string
  target_version: string
  changes: Array<{
    field: string
    old_value: any
    new_value: any
    reason: string
    severity: string
  }>
  migrated_config: Record<string, any>
  is_migrated: boolean
  required_count: number
  recommended_count: number
  optional_count: number
}

export interface RecommendationItem {
  id: number
  analysis_id: number
  category: string
  title: string
  description: string
  status: string
  created_at: string
  applied_at: string | null
  notes: string | null
}

export interface DiffEntry {
  path: string
  left_value: any
  right_value: any
  change_type: string
  section: string
}

export interface DiffResult {
  from_label: string
  to_label: string
  total_changes: number
  added_count: number
  removed_count: number
  changed_count: number
  parse_errors: string[]
  entries: DiffEntry[]
}

export interface GraphNode {
  id: string
  label: string
  type: string
  group: string
  color: string
  extra?: Record<string, unknown>
}

export interface GraphEdge {
  from: string
  to: string
  label: string
  type: string
}

export interface GraphResult {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export const analyzeConfig = (configContent: string) =>
  api.post<AnalyzeResult>('/analyze', { config_content: configContent })

export const runAudit = (configContent: string | null, configPath?: string) =>
  api.post<AuditResult>('/audit', { config_content: configContent, config_path: configPath })

export const getScore = (configContent: string | null, configPath?: string, detailed = false) =>
  api.post<ScoreResult>('/score', { config_content: configContent, config_path: configPath, detailed })

export const getHistory = (configPath?: string, limit = 10) =>
  api.get<{ records: HistoryRecord[]; total: number }>('/history', {
    params: { config_path: configPath, limit },
  })

export const getHistoryRecord = (id: number) =>
  api.get<HistoryRecord>(`/history/${id}`)

export const getTrend = (configPath?: string, limit = 20) =>
  api.get<{ data: TrendData[] }>('/history/trend', {
    params: { config_path: configPath, limit },
  })

export const runMigrate = (configContent: string | null, configPath?: string) =>
  api.post<MigrationResult>('/migrate', { config_content: configContent, config_path: configPath })

export const getRecommendations = (status?: string, limit = 50) =>
  api.get<{ recommendations: RecommendationItem[]; summary: Record<string, number> }>('/recommendations', {
    params: { status, limit },
  })

export const updateRecommendation = (id: number, status: string, notes?: string) =>
  api.patch<RecommendationItem>(`/recommendations/${id}`, { status, notes })

export const uploadConfig = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/config/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const validateConfig = (configPath: string) =>
  api.post('/config/validate', { config_path: configPath })

export const runDiff = (fromContent: string, toContent: string) =>
  api.post<DiffResult>('/diff', { from_content: fromContent, to_content: toContent })

export const runDiffCompare = (configContent: string | null, recordId: number, configPath?: string, dbPath?: string) =>
  api.post<DiffResult>('/diff/compare', {
    config_content: configContent,
    config_path: configPath,
    record_id: recordId,
    db_path: dbPath,
  })

export const getGraph = (configContent: string, configPath?: string, label?: string) =>
  api.post<GraphResult>('/graph', { config_content: configContent, config_path: configPath, label })

export default api
