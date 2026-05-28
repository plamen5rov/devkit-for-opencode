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
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Shield, Zap } from 'lucide-react'

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your OpenCode configuration health</p>
      </div>

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
          <CardHeader>
            <CardTitle>Recent Findings</CardTitle>
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
