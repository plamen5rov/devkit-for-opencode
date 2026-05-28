import { useQuery } from '@tanstack/react-query'
import { getHistory, getTrend } from '@/lib/api'
import { ScoreGauge } from '@/components/ScoreGauge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SeverityBadge } from '@/components/SeverityBadge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Shield, Zap, FileText, Clock, Lightbulb } from 'lucide-react'

export function Dashboard() {
  const { data: historyData } = useQuery({
    queryKey: ['history'],
    queryFn: () => getHistory(undefined, 1).then((r) => r.data),
  })

  const { data: trendData } = useQuery({
    queryKey: ['trend'],
    queryFn: () => getTrend(undefined, 20).then((r) => r.data),
  })

  const latest = historyData?.records[0]
  const healthScore = latest?.health_score ?? 0
  const riskScore = latest?.risk_score ?? 100

  const trendDirection = (() => {
    if (!trendData?.data || trendData.data.length < 2) return null
    const [a, b] = trendData.data
    return a.health_score > b.health_score ? 'up' : a.health_score < b.health_score ? 'down' : 'stable'
  })()

  const chartData = (trendData?.data ?? [])
    .map((d) => ({
      date: new Date(d.timestamp).toLocaleDateString(),
      health: d.health_score,
      risk: d.risk_score,
    }))
    .reverse()

  const severityCounts = (() => {
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
    latest?.findings?.forEach((f: any) => {
      const s = (f.severity ?? '').toLowerCase()
      if (s in counts) counts[s]++
    })
    return counts
  })()

  const severityColors: Record<string, string> = {
    critical: 'bg-red-600',
    high: 'bg-orange-500',
    medium: 'bg-amber-500',
    low: 'bg-blue-500',
    info: 'bg-slate-400',
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your OpenCode configuration health</p>
      </div>

      {latest && (
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5" />
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{latest.config_path}</code>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            {new Date(latest.timestamp).toLocaleString()}
          </span>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-center gap-8">
        <ScoreGauge score={healthScore} label="Health Score" />
        <ScoreGauge score={riskScore} label="Risk Score" />
        {trendDirection && (
          <div className="flex flex-col items-center gap-2">
            {trendDirection === 'up' && <TrendingUp className="h-10 w-10 text-emerald-500" />}
            {trendDirection === 'down' && <TrendingDown className="h-10 w-10 text-red-500" />}
            {trendDirection === 'stable' && <Minus className="h-10 w-10 text-amber-500" />}
            <span className="text-sm text-muted-foreground">Trend</span>
          </div>
        )}
      </div>

      {latest && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Issues</CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{latest.issue_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Warnings</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{latest.warning_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">MCP Token Estimate</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">~{latest.mcp_token_estimate.toLocaleString()}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Score Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" className="text-xs" />
                <YAxis domain={[0, 100]} className="text-xs" />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="health"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  name="Health Score"
                />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="hsl(var(--destructive))"
                  strokeWidth={2}
                  name="Risk Score"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {latest?.findings && latest.findings.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle>Recent Findings</CardTitle>
              <div className="flex items-center gap-2">
                {Object.entries(severityCounts)
                  .filter(([, count]) => count > 0)
                  .map(([severity, count]) => (
                    <span
                      key={severity}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-white ${severityColors[severity]}`}
                    >
                      {severity === 'critical' && 'C'}
                      {severity === 'high' && 'H'}
                      {severity === 'medium' && 'M'}
                      {severity === 'low' && 'L'}
                      {severity === 'info' && 'I'}
                      :&nbsp;{count}
                    </span>
                  ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severity</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Message</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {latest.findings.slice(0, 10).map((f, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <SeverityBadge severity={f.severity} />
                    </TableCell>
                    <TableCell className="font-medium">{f.category}</TableCell>
                    <TableCell className="text-muted-foreground">{f.message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {latest?.recommendations && latest.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-amber-500" />
              Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {latest.recommendations.map((rec: any, i: number) => (
                <div key={i} className="grid gap-1.5">
                  <div className="flex items-start gap-2">
                    <div
                      className={`mt-0.5 h-2 w-2 rounded-full shrink-0 ${rec.priority <= 1 ? 'bg-red-500' : rec.priority === 2 ? 'bg-amber-500' : 'bg-blue-500'}`}
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-medium leading-snug">{rec.title}</p>
                      <p className="text-sm text-muted-foreground mt-0.5">{rec.description}</p>
                      <div className="flex flex-wrap gap-2 mt-1.5">
                        <span className="inline-flex items-center px-1.5 py-0.5 text-xs rounded bg-muted text-muted-foreground">
                          Effort: {rec.effort}
                        </span>
                        <span className="inline-flex items-center px-1.5 py-0.5 text-xs rounded bg-muted text-muted-foreground">
                          {rec.category}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {!latest && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-lg text-muted-foreground">No analysis data yet</p>
            <p className="text-sm text-muted-foreground">Run an analysis to see your configuration health</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
