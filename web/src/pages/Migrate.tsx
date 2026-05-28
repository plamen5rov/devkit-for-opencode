import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { runMigrate } from '@/lib/api'
import { useSession } from '@/lib/SessionContext'
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
import { GitCompare, Loader2, Upload, Info, CheckCircle } from 'lucide-react'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { vscodeDark } from '@uiw/codemirror-theme-vscode'

export function MigratePage() {
  const { configContent, tabResults, setConfigContent, setTabResult } = useSession()
  const [configText, setConfigText] = useState(configContent)
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (configText) setConfigContent(configText)
  }, [configText, setConfigContent])

  useEffect(() => {
    setConfigText(configContent)
  }, [configContent])

  const migrateMutation = useMutation({
    mutationFn: ({ content, path }: { content: string | null; path?: string }) =>
      runMigrate(content, path),
  })

  const handleRun = () => {
    if (configText.trim()) {
      migrateMutation.mutate({ content: configText })
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
    if (migrateMutation.data?.data) {
      setTabResult('migrate', migrateMutation.data.data)
    }
  }, [migrateMutation.data, setTabResult])

  const result = migrateMutation.data?.data ?? tabResults.migrate
  const changes = result?.changes ?? []

  useEffect(() => {
    if (result) {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [result])

  const hasConfig = configText.trim().length > 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Migration Assistant</h1>
        <p className="text-muted-foreground">Detect deprecated fields and generate migration diffs</p>
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

          <Button onClick={handleRun} disabled={migrateMutation.isPending || !hasConfig}>
            {migrateMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <GitCompare className="mr-2 h-4 w-4" />
            )}
            Run Migration Analysis
          </Button>
        </CardContent>
      </Card>

      {!hasConfig && !result && (
        <Card className="border-blue-500/30 bg-blue-500/5">
          <CardContent className="pt-6 flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-blue-400">No configuration loaded</p>
              <p className="text-sm text-muted-foreground mt-1">
                Paste or upload an OpenCode config above, or run an analysis on the{' '}
                <span className="font-medium">Analyze</span> tab first to share config across tools.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {migrateMutation.isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">
              {(migrateMutation.error as any)?.response?.data?.detail ?? 'Migration failed'}
            </p>
          </CardContent>
        </Card>
      )}

      {result && (
        <div ref={resultsRef} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-500">{result.required_count}</div>
                  <div className="text-sm text-muted-foreground">Required</div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-amber-500">{result.recommended_count}</div>
                  <div className="text-sm text-muted-foreground">Recommended</div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-500">{result.optional_count}</div>
                  <div className="text-sm text-muted-foreground">Optional</div>
                </div>
              </CardContent>
            </Card>
          </div>

          {changes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Changes ({changes.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Severity</TableHead>
                      <TableHead>Field</TableHead>
                      <TableHead>Old Value</TableHead>
                      <TableHead>New Value</TableHead>
                      <TableHead>Reason</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {changes.map((c: any, i: number) => (
                      <TableRow key={i}>
                        <TableCell>
                          <SeverityBadge severity={c.severity} />
                        </TableCell>
                        <TableCell className="font-mono text-xs">{c.field}</TableCell>
                        <TableCell className="font-mono text-xs">
                          {typeof c.old_value === 'object'
                            ? JSON.stringify(c.old_value).slice(0, 30)
                            : String(c.old_value)}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {typeof c.new_value === 'object'
                            ? JSON.stringify(c.new_value).slice(0, 30)
                            : String(c.new_value)}
                        </TableCell>
                        <TableCell className="text-muted-foreground">{c.reason}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {changes.length === 0 && (
            <Card className="border-emerald-500/30 bg-emerald-500/5">
              <CardContent className="pt-6 flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <p className="font-medium text-emerald-400">No deprecated fields detected</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Your configuration is up to date. No migration changes are needed.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {result.is_migrated && result.migrated_config && (
            <Card>
              <CardHeader>
                <CardTitle>Migrated Config</CardTitle>
              </CardHeader>
              <CardContent>
                <CodeMirror
                  value={JSON.stringify(result.migrated_config, null, 2)}
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
