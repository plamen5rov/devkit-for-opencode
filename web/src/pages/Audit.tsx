import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { runAudit } from '@/lib/api'
import { useSession } from '@/lib/SessionContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SeverityBadge } from '@/components/SeverityBadge'
import { ScoreGauge } from '@/components/ScoreGauge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { vscodeDark } from '@uiw/codemirror-theme-vscode'
import { Shield, Loader2, Filter, Upload } from 'lucide-react'

const severities = ['all', 'critical', 'high', 'medium', 'low', 'info']

export function AuditPage() {
  const { configContent, tabResults, setConfigContent, setTabResult } = useSession()
  const [configText, setConfigText] = useState(configContent)
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [filterSeverity, setFilterSeverity] = useState('all')
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (configText) setConfigContent(configText)
  }, [configText, setConfigContent])

  const auditMutation = useMutation({
    mutationFn: ({ content, path }: { content: string | null; path?: string }) =>
      runAudit(content, path),
  })

  const handleRun = () => {
    if (configText.trim()) {
      auditMutation.mutate({ content: configText })
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      const reader = new FileReader()
      reader.onload = (ev) => {
        const text = ev.target?.result as string
        setConfigText(text)
      }
      reader.readAsText(file)
    }
  }

  useEffect(() => {
    if (auditMutation.data?.data) {
      setTabResult('audit', auditMutation.data.data)
    }
  }, [auditMutation.data, setTabResult])

  const result = auditMutation.data?.data ?? tabResults.audit
  const findings = result?.findings ?? []
  const filtered = filterSeverity === 'all'
    ? findings
    : findings.filter((f: any) => f.severity === filterSeverity)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Security Audit</h1>
        <p className="text-muted-foreground">Scan for security issues and anti-patterns</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-1 border-b">
            {(['paste', 'upload'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === tab ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
              >
                {tab === 'paste' ? 'Paste JSON' : 'Upload File'}
              </button>
            ))}
          </div>

          {activeTab === 'paste' && (
            <CodeMirror
              value={configText}
              onChange={setConfigText}
              height="200px"
              extensions={[json()]}
              theme={vscodeDark}
              placeholder='Paste your opencode.json here...'
              basicSetup={{ lineNumbers: true, foldGutter: true }}
            />
          )}

          {activeTab === 'upload' && (
            <div className="space-y-2">
              <input
                ref={fileRef}
                type="file"
                accept=".json,.jsonc"
                onChange={handleFileUpload}
                className="hidden"
              />
              <Button variant="outline" onClick={() => fileRef.current?.click()}>
                <Upload className="mr-2 h-4 w-4" />
                {selectedFile ? selectedFile.name : 'Choose File'}
              </Button>
            </div>
          )}

          <Button onClick={handleRun} disabled={auditMutation.isPending || !configText.trim()}>
            {auditMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Shield className="mr-2 h-4 w-4" />
            )}
            Run Security Audit
          </Button>
        </CardContent>
      </Card>

      {auditMutation.isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">
              {(auditMutation.error as any)?.response?.data?.detail ?? 'Audit failed'}
            </p>
          </CardContent>
        </Card>
      )}

      {result && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-8">
            <ScoreGauge score={result.risk_score} label="Risk Score" />
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              {(['critical', 'high', 'medium', 'low', 'info'] as const).map((sev) => (
                <div key={sev} className="text-center">
                  <div className="text-2xl font-bold">
                    {result[`${sev}_count` as keyof typeof result] as number}
                  </div>
                  <div className="text-xs text-muted-foreground capitalize">{sev}</div>
                </div>
              ))}
            </div>
          </div>

          {filtered.length > 0 && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Findings ({filtered.length})</CardTitle>
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <select
                    className="rounded-md border bg-background px-2 py-1 text-sm"
                    value={filterSeverity}
                    onChange={(e) => setFilterSeverity(e.target.value)}
                  >
                    {severities.map((s) => (
                      <option key={s} value={s}>
                        {s === 'all' ? 'All Severities' : s.charAt(0).toUpperCase() + s.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Severity</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Title</TableHead>
                      <TableHead>Remediation</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.map((f: any, i: number) => (
                      <TableRow key={i}>
                        <TableCell>
                          <SeverityBadge severity={f.severity} />
                        </TableCell>
                        <TableCell className="font-medium">{f.category}</TableCell>
                        <TableCell>{f.title}</TableCell>
                        <TableCell className="text-muted-foreground">{f.remediation}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
