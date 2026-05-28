import { useState, useMemo, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { analyzeConfig, uploadConfig } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
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
import { Upload, Play, Loader2, Clipboard, Wrench, Check, Copy } from 'lucide-react'

type TabType = 'upload' | 'paste'

interface FixItem {
  id: string
  label: string
  category: 'issue' | 'warning' | 'recommendation'
  apply: (config: any) => any
}

function detectFixes(config: any, result: any): FixItem[] {
  const fixes: FixItem[] = []
  const issues = result?.orchestrator?.issues ?? []
  const warnings = result?.orchestrator?.warnings ?? []
  const perms = config?.permission ?? {}

  // Missing catch-all
  if (typeof perms === 'object' && !('*' in perms)) {
    fixes.push({
      id: 'catch-all',
      label: 'Add catch-all permission rule ("*": "ask")',
      category: 'issue',
      apply: (c) => ({ ...c, permission: { ...c.permission, '*': 'ask' } }),
    })
  }

  // Global bash allow
  if (perms?.bash === 'allow') {
    fixes.push({
      id: 'bash-allow',
      label: 'Restrict global bash permission (allow → ask)',
      category: 'issue',
      apply: (c) => ({ ...c, permission: { ...c.permission, bash: 'ask' } }),
    })
  }

  // Global edit allow
  if (perms?.edit === 'allow') {
    fixes.push({
      id: 'edit-allow',
      label: 'Restrict global edit permission (allow → ask)',
      category: 'warning',
      apply: (c) => ({ ...c, permission: { ...c.permission, edit: 'ask' } }),
    })
  }

  // Missing small_model
  if (!config?.small_model) {
    fixes.push({
      id: 'small-model',
      label: 'Add small_model for cost-efficient operations',
      category: 'warning',
      apply: (c) => ({ ...c, small_model: 'anthropic/claude-haiku-4-20250514' }),
    })
  }

  // Missing $schema
  if (!config?.['$schema']) {
    fixes.push({
      id: 'schema',
      label: 'Add $schema reference for IDE support',
      category: 'warning',
      apply: (c) => ({ ...c, $schema: 'https://opencode.ai/config.json' }),
    })
  }

  // Missing share config
  if (!config?.share) {
    fixes.push({
      id: 'share',
      label: 'Add share configuration (set to "manual")',
      category: 'warning',
      apply: (c) => ({ ...c, share: 'manual' }),
    })
  }

  // Model without provider prefix
  const model = config?.model ?? ''
  if (model && typeof model === 'string' && !model.includes('/')) {
    const prefix = model.toLowerCase().includes('claude') ? 'anthropic' :
                   model.toLowerCase().includes('gpt') || model.toLowerCase().includes('o1') ? 'openai' :
                   model.toLowerCase().includes('gemini') ? 'google' : 'anthropic'
    fixes.push({
      id: 'model-prefix',
      label: `Add provider prefix to model ("${model}" → "${prefix}/${model}")`,
      category: 'issue',
      apply: (c) => ({ ...c, model: `${prefix}/${model}` }),
    })
  }

  // Disabled MCP servers
  const mcpServers = config?.mcp?.servers ?? {}
  if (typeof mcpServers === 'object') {
    for (const [name, server] of Object.entries(mcpServers)) {
      if (typeof server === 'object' && !(server as any).enabled) {
        fixes.push({
          id: `mcp-${name}`,
          label: `Remove disabled MCP server "${name}"`,
          category: 'warning',
          apply: (c) => {
            const { [name]: _, ...rest } = c.mcp.servers
            return { ...c, mcp: { ...c.mcp, servers: rest } }
          },
        })
      }
    }
  }

  return fixes
}

function applyFixes(config: any, selectedIds: Set<string>, fixes: FixItem[]): any {
  let patched = { ...config }
  for (const fix of fixes) {
    if (selectedIds.has(fix.id)) {
      patched = fix.apply(patched)
    }
  }
  return patched
}

export function AnalyzePage() {
  const [configText, setConfigText] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('paste')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedFixes, setSelectedFixes] = useState<Set<string>>(new Set())
  const [fixedConfigText, setFixedConfigText] = useState('')
  const [copied, setCopied] = useState(false)

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
      setSelectedFixes(new Set())
      setFixedConfigText('')
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

  const parsedConfig = useMemo(() => {
    try {
      return JSON.parse(configText)
    } catch {
      return null
    }
  }, [configText])

  const fixes = useMemo(() => {
    if (!parsedConfig || !result) return []
    return detectFixes(parsedConfig, result)
  }, [parsedConfig, result])

  const fixableCount = fixes.length

  const handleToggleFix = useCallback((id: string) => {
    setSelectedFixes((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const handleFixAll = useCallback(() => {
    if (selectedFixes.size === fixableCount) {
      setSelectedFixes(new Set())
    } else {
      setSelectedFixes(new Set(fixes.map((f) => f.id)))
    }
  }, [fixes, fixableCount, selectedFixes.size])

  const handleGenerateFixed = useCallback(() => {
    if (!parsedConfig || fixes.length === 0) return
    const patched = applyFixes(parsedConfig, selectedFixes, fixes)
    setFixedConfigText(JSON.stringify(patched, null, 2))
  }, [parsedConfig, selectedFixes, fixes])

  const handleCopyFixed = useCallback(() => {
    navigator.clipboard.writeText(fixedConfigText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [fixedConfigText])

  const issueFixes = fixes.filter((f) => f.category === 'issue')
  const warningFixes = fixes.filter((f) => f.category === 'warning')

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

          {issueFixes.length > 0 && (
            <Card className="border-red-500/60 bg-red-500/5 dark:bg-red-500/10">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-500">
                  <span className="h-3 w-3 rounded-full bg-red-500" />
                  Issues ({issueFixes.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {issueFixes.map((fix) => (
                    <li key={fix.id} className="flex items-start gap-3">
                      <Checkbox
                        id={`fix-${fix.id}`}
                        checked={selectedFixes.has(fix.id)}
                        onCheckedChange={() => handleToggleFix(fix.id)}
                        className="mt-0.5 border-red-400 data-[state=checked]:bg-red-500 data-[state=checked]:border-red-500"
                      />
                      <label
                        htmlFor={`fix-${fix.id}`}
                        className="cursor-pointer text-sm leading-relaxed"
                      >
                        {fix.label}
                      </label>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {warningFixes.length > 0 && (
            <Card className="border-yellow-500/60 bg-yellow-500/5 dark:bg-yellow-500/10">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-yellow-500">
                  <span className="h-3 w-3 rounded-full bg-yellow-500" />
                  Warnings ({warningFixes.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {warningFixes.map((fix) => (
                    <li key={fix.id} className="flex items-start gap-3">
                      <Checkbox
                        id={`fix-${fix.id}`}
                        checked={selectedFixes.has(fix.id)}
                        onCheckedChange={() => handleToggleFix(fix.id)}
                        className="mt-0.5 border-yellow-400 data-[state=checked]:bg-yellow-500 data-[state=checked]:border-yellow-500"
                      />
                      <label
                        htmlFor={`fix-${fix.id}`}
                        className="cursor-pointer text-sm leading-relaxed"
                      >
                        {fix.label}
                      </label>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {fixableCount > 0 && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleFixAll}
                  >
                    {selectedFixes.size === fixableCount ? 'Deselect All' : 'Fix All'}
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {selectedFixes.size} of {fixableCount} selected
                  </span>
                  <Button
                    onClick={handleGenerateFixed}
                    disabled={selectedFixes.size === 0}
                    className="ml-auto"
                  >
                    <Wrench className="mr-2 h-4 w-4" />
                    Generate Fixed Config
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {fixedConfigText && (
            <Card className="border-green-500/60">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-green-500">
                    <Check className="h-5 w-5" />
                    Fixed Configuration
                  </span>
                  <Button variant="outline" size="sm" onClick={handleCopyFixed}>
                    {copied ? (
                      <><Check className="mr-2 h-4 w-4" /> Copied!</>
                    ) : (
                      <><Copy className="mr-2 h-4 w-4" /> Copy</>
                    )}
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CodeMirror
                  value={fixedConfigText}
                  height="400px"
                  extensions={[json()]}
                  theme={vscodeDark}
                  basicSetup={{ lineNumbers: true, foldGutter: true }}
                  editable={false}
                />
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
                    <Card className="border-blue-500/40 bg-blue-500/5 dark:bg-blue-500/10">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-sm text-blue-500">
                          <span className="h-2.5 w-2.5 rounded-full bg-blue-500" />
                          Permissions
                        </CardTitle>
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
                    <Card className="border-violet-500/40 bg-violet-500/5 dark:bg-violet-500/10">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-sm text-violet-500">
                          <span className="h-2.5 w-2.5 rounded-full bg-violet-500" />
                          Agents
                        </CardTitle>
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
                    <Card className="border-emerald-500/40 bg-emerald-500/5 dark:bg-emerald-500/10">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-sm text-emerald-500">
                          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                          Skills
                        </CardTitle>
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
                    <Card className="border-amber-500/40 bg-amber-500/5 dark:bg-amber-500/10">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-sm text-amber-500">
                          <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                          MCP Servers
                        </CardTitle>
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
                    <Card className="border-cyan-500/40 bg-cyan-500/5 dark:bg-cyan-500/10">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-sm text-cyan-500">
                          <span className="h-2.5 w-2.5 rounded-full bg-cyan-500" />
                          Commands
                        </CardTitle>
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
