import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { runDiff, runDiffCompare, type DiffResult, type DiffEntry } from '@/lib/api'
import { useSession } from '@/lib/SessionContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { GitCompare, Loader2, Upload, Info, ArrowRightLeft,
  AlertTriangle,
} from 'lucide-react'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { vscodeDark } from '@uiw/codemirror-theme-vscode'

const CHANGE_COLORS: Record<string, string> = {
  added: 'text-emerald-400',
  removed: 'text-red-400',
  changed: 'text-amber-400',
}

const CHANGE_BG: Record<string, string> = {
  added: 'bg-emerald-950/40 border-emerald-800',
  removed: 'bg-red-950/40 border-red-800',
  changed: 'bg-amber-950/40 border-amber-800',
}

const SECTION_ORDER = [
  'model', 'small_model', 'permission', 'agent', 'mcp',
  'plugin', 'share', 'snapshot', 'autoupdate', 'tools',
  'command', 'skill', 'theme', 'keys', 'other',
]

function groupBySection(entries: DiffEntry[]): Record<string, DiffEntry[]> {
  const groups: Record<string, DiffEntry[]> = {}
  for (const e of entries) {
    if (!groups[e.section]) groups[e.section] = []
    groups[e.section].push(e)
  }
  return groups
}

function getFieldLabel(path: string): string {
  const parts = path.split('.')
  if (parts.length === 1) return parts[0]
  if (parts.length === 2) return parts[1]
  return parts.slice(parts.length - 2).join('.')
}

export function DiffPage() {
  const { configContent } = useSession()
  const [fromText, setFromText] = useState(configContent)
  const [toText, setToText] = useState('')
  const [fromActiveTab, setFromActiveTab] = useState<'paste' | 'upload'>('paste')
  const [toActiveTab, setToActiveTab] = useState<'paste' | 'upload'>('paste')
  const [fromFile, setFromFile] = useState<File | null>(null)
  const [toFile, setToFile] = useState<File | null>(null)
  const fromFileRef = useRef<HTMLInputElement>(null)
  const toFileRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  const diffMutation = useMutation({
    mutationFn: ({ from, to }: { from: string; to: string }) =>
      runDiff(from, to),
  })

  useEffect(() => {
    if (diffMutation.data?.data) {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [diffMutation.data])

  const handleRun = () => {
    if (fromText.trim() && toText.trim()) {
      diffMutation.mutate({ from: fromText, to: toText })
    }
  }

  const getFileText = (file: File, setter: (text: string) => void) => {
    const reader = new FileReader()
    reader.onload = (ev) => setter(ev.target?.result as string)
    reader.readAsText(file)
  }

  const handleFromUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setFromFile(f)
      getFileText(f, setFromText)
    }
  }

  const handleToUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setToFile(f)
      getFileText(f, setToText)
    }
  }

  const result = diffMutation.data?.data as DiffResult | null
  const entries = result?.entries ?? []
  const grouped = groupBySection(entries)
  const sortedSections = SECTION_ORDER.filter((s) => grouped[s])

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold tracking-tight">Config Diff</h2>
      <p className="text-muted-foreground">
        Compare two OpenCode configs side by side to see what changed.
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <ArrowRightLeft className="h-4 w-4 text-blue-400" />
              From (Source)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Button
                variant={fromActiveTab === 'paste' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFromActiveTab('paste')}
              >
                Paste JSON
              </Button>
              <Button
                variant={fromActiveTab === 'upload' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFromActiveTab('upload')}
              >
                <Upload className="mr-1 h-3 w-3" />
                Upload File
              </Button>
            </div>
            {fromActiveTab === 'paste' ? (
              <CodeMirror
                value={fromText}
                onChange={setFromText}
                extensions={[json()]}
                theme={vscodeDark}
                height="250px"
                placeholder="Paste source OpenCode config JSON..."
              />
            ) : (
              <div className="rounded-lg border border-dashed p-6 text-center">
                <input
                  ref={fromFileRef}
                  type="file"
                  accept=".json,.jsonc"
                  onChange={handleFromUpload}
                  className="hidden"
                />
                <Upload className="mx-auto h-6 w-6 text-muted-foreground" />
                <p className="mt-2 text-sm text-muted-foreground">
                  {fromFile ? fromFile.name : 'Drop or select a config file'}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => fromFileRef.current?.click()}
                >
                  Choose File
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <ArrowRightLeft className="h-4 w-4 text-emerald-400" />
              To (Target)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Button
                variant={toActiveTab === 'paste' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setToActiveTab('paste')}
              >
                Paste JSON
              </Button>
              <Button
                variant={toActiveTab === 'upload' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setToActiveTab('upload')}
              >
                <Upload className="mr-1 h-3 w-3" />
                Upload File
              </Button>
            </div>
            {toActiveTab === 'paste' ? (
              <CodeMirror
                value={toText}
                onChange={setToText}
                extensions={[json()]}
                theme={vscodeDark}
                height="250px"
                placeholder="Paste target OpenCode config JSON..."
              />
            ) : (
              <div className="rounded-lg border border-dashed p-6 text-center">
                <input
                  ref={toFileRef}
                  type="file"
                  accept=".json,.jsonc"
                  onChange={handleToUpload}
                  className="hidden"
                />
                <Upload className="mx-auto h-6 w-6 text-muted-foreground" />
                <p className="mt-2 text-sm text-muted-foreground">
                  {toFile ? toFile.name : 'Drop or select a config file'}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => toFileRef.current?.click()}
                >
                  Choose File
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-center">
        <Button
          onClick={handleRun}
          disabled={!fromText.trim() || !toText.trim() || diffMutation.isPending}
          className="gap-2"
        >
          {diffMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <GitCompare className="h-4 w-4" />
          )}
          Compare Configs
        </Button>
      </div>

      {result && (
        <div ref={resultsRef} className="space-y-6">
          {result.parse_errors && result.parse_errors.length > 0 && (
            <Card className="border-red-800 bg-red-950/30">
              <CardContent className="flex flex-col gap-2 py-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-400" />
                  <span className="font-semibold text-red-300">Parse Error</span>
                </div>
                {result.parse_errors.map((err, i) => (
                  <p key={i} className="text-sm text-red-200/80 font-mono">{err}</p>
                ))}
                <p className="text-xs text-red-300/60">
                  Common JSONC issues: trailing commas, missing quotes, or unescaped characters.
                  Fix the config and re-run the comparison.
                </p>
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <GitCompare className="h-5 w-5" />
                Diff Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <div className="rounded-lg border bg-emerald-950/30 px-4 py-2">
                  <div className="text-2xl font-bold text-emerald-400">{result.added_count}</div>
                  <div className="text-xs text-muted-foreground">Added</div>
                </div>
                <div className="rounded-lg border bg-red-950/30 px-4 py-2">
                  <div className="text-2xl font-bold text-red-400">{result.removed_count}</div>
                  <div className="text-xs text-muted-foreground">Removed</div>
                </div>
                <div className="rounded-lg border bg-amber-950/30 px-4 py-2">
                  <div className="text-2xl font-bold text-amber-400">{result.changed_count}</div>
                  <div className="text-xs text-muted-foreground">Changed</div>
                </div>
                <div className="rounded-lg border px-4 py-2">
                  <div className="text-2xl font-bold">{result.total_changes}</div>
                  <div className="text-xs text-muted-foreground">Total</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {entries.length === 0 ? (
            <Card className="border-emerald-800 bg-emerald-950/20">
              <CardContent className="flex items-center gap-3 py-6">
                <Info className="h-5 w-5 text-emerald-400" />
                <p className="text-emerald-300">Configs are identical — no differences found.</p>
              </CardContent>
            </Card>
          ) : (
            sortedSections.map((section) => {
              const sectionEntries = grouped[section]
              return (
                <Card key={section}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base capitalize">{section}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-32">Type</TableHead>
                          <TableHead className="w-40">Field</TableHead>
                          <TableHead>From Value</TableHead>
                          <TableHead>To Value</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sectionEntries.map((entry, i) => (
                          <TableRow key={i} className={CHANGE_BG[entry.change_type] || ''}>
                            <TableCell>
                              <span className={`text-xs font-semibold uppercase ${CHANGE_COLORS[entry.change_type] || ''}`}>
                                {entry.change_type}
                              </span>
                            </TableCell>
                            <TableCell className="font-mono text-xs">{getFieldLabel(entry.path)}</TableCell>
                            <TableCell className="font-mono text-xs max-w-[250px] truncate">
                              {renderValue(entry.left_value)}
                            </TableCell>
                            <TableCell className="font-mono text-xs max-w-[250px] truncate">
                              {renderValue(entry.right_value)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

function renderValue(val: unknown): string {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}
