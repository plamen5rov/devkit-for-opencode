import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getHistory, getHistoryRecord, HistoryRecord } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SeverityBadge } from '@/components/SeverityBadge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ScoreGauge } from '@/components/ScoreGauge'
import { Clock, ChevronRight, Loader2 } from 'lucide-react'

export function HistoryPage() {
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data: historyData, isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: () => getHistory(undefined, 50).then((r) => r.data),
  })

  const { data: selectedRecord, isLoading: isLoadingRecord } = useQuery({
    queryKey: ['history', selectedId],
    queryFn: () => getHistoryRecord(selectedId!).then((r) => r.data),
    enabled: selectedId !== null,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">History</h1>
        <p className="text-muted-foreground">Timeline of past analyses</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Analysis Records ({historyData?.total ?? 0})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead></TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Config Path</TableHead>
                  <TableHead>Health</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Issues</TableHead>
                  <TableHead>Warnings</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historyData?.records.map((record) => (
                  <TableRow
                    key={record.id}
                    className="cursor-pointer"
                    onClick={() => setSelectedId(record.id)}
                    data-state={selectedId === record.id ? 'selected' : undefined}
                  >
                    <TableCell>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </TableCell>
                    <TableCell>
                      {new Date(record.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {record.config_path}
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          record.health_score >= 80
                            ? 'text-emerald-500'
                            : record.health_score >= 50
                              ? 'text-amber-500'
                              : 'text-red-500'
                        }
                      >
                        {record.health_score}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          record.risk_score >= 80
                            ? 'text-emerald-500'
                            : record.risk_score >= 50
                              ? 'text-amber-500'
                              : 'text-red-500'
                        }
                      >
                        {record.risk_score}
                      </span>
                    </TableCell>
                    <TableCell>{record.issue_count}</TableCell>
                    <TableCell>{record.warning_count}</TableCell>
                  </TableRow>
                ))}
                {(!historyData?.records || historyData.records.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No records found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {isLoadingRecord && (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      )}

      {selectedRecord && (
        <Card>
          <CardHeader>
            <CardTitle>Record Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-center gap-8">
              <ScoreGauge score={selectedRecord.health_score} label="Health Score" />
              <ScoreGauge score={selectedRecord.risk_score} label="Risk Score" />
            </div>

            {selectedRecord.findings && selectedRecord.findings.length > 0 && (
              <div>
                <h3 className="mb-2 text-lg font-semibold">Findings</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Severity</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Message</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedRecord.findings.map((f, i) => (
                      <TableRow key={i}>
                        <TableCell>
                          <SeverityBadge severity={f.severity} />
                        </TableCell>
                        <TableCell>{f.category}</TableCell>
                        <TableCell className="text-muted-foreground">{f.message}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
