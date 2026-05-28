import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { runMigrate } from '@/lib/api'
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
import { GitCompare, Loader2 } from 'lucide-react'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { vscodeDark } from '@uiw/codemirror-theme-vscode'

export function MigratePage() {
  const [configPath, setConfigPath] = useState('')

  const migrateMutation = useMutation({
    mutationFn: (path?: string) => runMigrate(path),
  })

  const handleRun = () => {
    migrateMutation.mutate(configPath || undefined)
  }

  const result = migrateMutation.data?.data
  const changes = result?.changes ?? []

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
          <input
            type="text"
            placeholder="~/.config/opencode/opencode.json"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            value={configPath}
            onChange={(e) => setConfigPath(e.target.value)}
          />
          <Button onClick={handleRun} disabled={migrateMutation.isPending}>
            {migrateMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <GitCompare className="mr-2 h-4 w-4" />
            )}
            Run Migration Analysis
          </Button>
        </CardContent>
      </Card>

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
        <div className="space-y-4">
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
                    {changes.map((c, i) => (
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
