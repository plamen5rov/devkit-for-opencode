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

          {result.orchestrator?.issues && result.orchestrator.issues.length > 0 && (
            <Card className="border-destructive/50">
              <CardHeader>
                <CardTitle className="text-destructive">Issues ({result.orchestrator.issues.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.orchestrator.issues.map((issue: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-destructive" />
                      <span>{issue}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {result.orchestrator?.warnings && result.orchestrator.warnings.length > 0 && (
            <Card className="border-yellow-500/50">
              <CardHeader>
                <CardTitle className="text-yellow-500">Warnings ({result.orchestrator.warnings.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.orchestrator.warnings.map((warning: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-yellow-500" />
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {findings.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Audit Findings ({findings.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Severity</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Message</TableHead>
                      <TableHead className="max-w-xs">Suggestion</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {findings.map((f: any, i: number) => (
                      <TableRow key={i}>
                        <TableCell>
                          <SeverityBadge severity={f.severity} />
                        </TableCell>
                        <TableCell className="font-mono text-xs">{f.category}</TableCell>
                        <TableCell className="font-medium">{f.message}</TableCell>
                        <TableCell className="max-w-xs text-muted-foreground">{f.suggestion}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {result.optimization?.recommendations && result.optimization.recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recommendations ({result.optimization.recommendations.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Priority</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Title</TableHead>
                      <TableHead className="max-w-xs">Impact</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.optimization.recommendations.map((r: any, i: number) => (
                      <TableRow key={i}>
                        <TableCell>
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            r.priority <= 2 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                            r.priority <= 3 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                            'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                          }`}>
                            P{r.priority}
                          </span>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{r.category}</TableCell>
                        <TableCell className="font-medium">{r.title}</TableCell>
                        <TableCell className="max-w-xs text-muted-foreground">{r.estimated_impact}</TableCell>
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
                <CardTitle>Analysis Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {result.raw_analyses.permissions && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Permissions</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Total rules</span>
                            <span className="font-mono">{result.raw_analyses.permissions.total_rules}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Issues</span>
                            <span className="font-mono">{result.raw_analyses.permissions.issues?.length ?? 0}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Warnings</span>
                            <span className="font-mono">{result.raw_analyses.permissions.warnings?.length ?? 0}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  {result.raw_analyses.agents && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Agents</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Total</span>
                            <span className="font-mono">{result.raw_analyses.agents.total_agents}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Dependencies</span>
                            <span className="font-mono">{result.raw_analyses.agents.total_dependencies}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  {result.raw_analyses.skills && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Skills</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Total</span>
                            <span className="font-mono">{result.raw_analyses.skills.total_skills}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Valid</span>
                            <span className="font-mono">{result.raw_analyses.skills.valid_skills}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  {result.raw_analyses.mcp_servers && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">MCP Servers</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Enabled</span>
                            <span className="font-mono">{result.raw_analyses.mcp_servers.enabled_count}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Disabled</span>
                            <span className="font-mono">{result.raw_analyses.mcp_servers.disabled_count}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Token est.</span>
                            <span className="font-mono">~{result.raw_analyses.mcp_servers.total_estimated_tokens}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                  {result.raw_analyses.commands && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Commands</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Total</span>
                            <span className="font-mono">{result.raw_analyses.commands.total_commands}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
