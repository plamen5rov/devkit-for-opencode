import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { analyzeConfig, uploadConfig } from '@/lib/api'
import { Button } from '@/components/ui/button'
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
import { ScoreGauge } from '@/components/ScoreGauge'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { vscodeDark } from '@uiw/codemirror-theme-vscode'
import { Upload, Play, Loader2, Clipboard } from 'lucide-react'

type TabType = 'upload' | 'paste'

export function AnalyzePage() {
  const [configText, setConfigText] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('paste')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const analyzeMutation = useMutation({
    mutationFn: (content: string) => analyzeConfig(content),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadConfig(file),
    onSuccess: (res) => {
      const content = (res.data as any).content
      setConfigText(content)
      if (content) {
        analyzeMutation.mutate(content)
      }
    },
  })

  const handleRun = () => {
    if (configText.trim()) {
      analyzeMutation.mutate(configText)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      const reader = new FileReader()
      reader.onload = (ev) => {
        setConfigText(ev.target?.result as string)
      }
      reader.readAsText(file)
    }
  }

  const result = analyzeMutation.data?.data
  const summary = result?.orchestrator?.summary ?? {}
  const findings = result?.audit?.findings ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analyze</h1>
        <p className="text-muted-foreground">Paste or upload an OpenCode configuration for analysis</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              variant={activeTab === 'paste' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('paste')}
            >
              <Clipboard className="mr-2 h-4 w-4" />
              Paste JSON
            </Button>
            <Button
              variant={activeTab === 'upload' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('upload')}
            >
              <Upload className="mr-2 h-4 w-4" />
              Upload File
            </Button>
          </div>

          {activeTab === 'paste' && (
            <CodeMirror
              value={configText}
              height="350px"
              extensions={[json()]}
              theme={vscodeDark}
              basicSetup={{ lineNumbers: true, foldGutter: true }}
              onChange={(value) => setConfigText(value)}
              placeholder={'Paste your opencode.json here...'}
            />
          )}

          {activeTab === 'upload' && (
            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 hover:bg-muted/50">
              <Upload className="h-8 w-8 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {selectedFile ? selectedFile.name : 'Click to upload opencode.json or .jsonc'}
              </span>
              <input
                type="file"
                accept=".json,.jsonc"
                className="hidden"
                onChange={handleFileUpload}
              />
            </label>
          )}

          <Button
            onClick={handleRun}
            disabled={analyzeMutation.isPending || !configText.trim()}
          >
            {analyzeMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Run Analysis
          </Button>
        </CardContent>
      </Card>

      {analyzeMutation.isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">
              {(analyzeMutation.error as any)?.response?.data?.detail ?? 'Analysis failed'}
            </p>
          </CardContent>
        </Card>
      )}

      {result && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-8">
            <ScoreGauge score={summary.health_score ?? 0} label="Health Score" />
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {[
                ['Issues', summary.total_issues ?? 0],
                ['Warnings', summary.total_warnings ?? 0],
                ['Agents', summary.agent_count ?? 0],
                ['Skills', summary.skill_count ?? 0],
                ['MCP Servers', summary.mcp_count ?? 0],
                ['Commands', summary.command_count ?? 0],
              ].map(([label, value]) => (
                <div key={label} className="text-center">
                  <div className="text-2xl font-bold">{value}</div>
                  <div className="text-xs text-muted-foreground">{label}</div>
                </div>
              ))}
            </div>
          </div>

          {findings.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Findings ({findings.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Severity</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Title</TableHead>
                      <TableHead>Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {findings.map((f: any, i: number) => (
                      <TableRow key={i}>
                        <TableCell>
                          <SeverityBadge severity={f.severity} />
                        </TableCell>
                        <TableCell className="font-mono text-xs">{f.category}</TableCell>
                        <TableCell className="font-medium">{f.title}</TableCell>
                        <TableCell className="max-w-md truncate text-muted-foreground">
                          {f.description}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {result.raw_analyses && (
            <Card>
              <CardHeader>
                <CardTitle>Raw Analyses</CardTitle>
              </CardHeader>
              <CardContent>
                <CodeMirror
                  value={JSON.stringify(result.raw_analyses, null, 2)}
                  height="400px"
                  extensions={[json()]}
                  theme={vscodeDark}
                  basicSetup={{ lineNumbers: true, foldGutter: true }}
                  editable={false}
                />
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
