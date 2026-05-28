import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { getScore } from '@/lib/api'
import { useSession } from '@/lib/SessionContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScoreGauge } from '@/components/ScoreGauge'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { vscodeDark } from '@uiw/codemirror-theme-vscode'
import { Loader2, Upload } from 'lucide-react'

export function ScorePage() {
  const { configContent, tabResults, setConfigContent, setTabResult } = useSession()
  const [configText, setConfigText] = useState(configContent)
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [detailed, setDetailed] = useState(true)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (configText) setConfigContent(configText)
  }, [configText, setConfigContent])

  useEffect(() => {
    setConfigText(configContent)
  }, [configContent])

  const scoreMutation = useMutation({
    mutationFn: ({ content, path, detailed }: { content: string | null; path?: string; detailed: boolean }) =>
      getScore(content, path, detailed),
  })

  const handleRun = () => {
    if (configText.trim()) {
      scoreMutation.mutate({ content: configText, detailed })
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
    if (scoreMutation.data?.data) {
      setTabResult('score', scoreMutation.data.data)
    }
  }, [scoreMutation.data, setTabResult])

  const result = scoreMutation.data?.data ?? tabResults.score
  const breakdown = result?.breakdown

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Health Score</h1>
        <p className="text-muted-foreground">Detailed configuration health breakdown</p>
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

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={detailed}
                onChange={(e) => setDetailed(e.target.checked)}
              />
              Detailed
            </label>
            <Button onClick={handleRun} disabled={scoreMutation.isPending || !configText.trim()}>
              {scoreMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Calculate Score
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          <div className="flex justify-center">
            <ScoreGauge score={result.health_score} label="Health Score" size={160} />
          </div>

          {breakdown && (
            <Card className="max-w-2xl">
              <CardHeader>
                <CardTitle>Factor Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {Object.entries(breakdown).map(([key, value]) => (
                  <div key={key} className="flex items-center py-1.5 border-b border-dashed border-border/40 last:border-0">
                    <span className="text-sm capitalize shrink-0">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="grow mx-3 border-b border-dotted border-muted-foreground/25 mt-[0.4em]" />
                    <span className="font-mono text-sm font-medium shrink-0 tabular-nums">
                      {typeof value === 'number' ? value.toLocaleString() : String(value)}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {result.summary && (
            <Card className="max-w-2xl">
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {Object.entries(result.summary).map(([key, value]) => (
                  <div key={key} className="flex items-center py-1.5 border-b border-dashed border-border/40 last:border-0">
                    <span className="text-sm capitalize shrink-0">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="grow mx-3 border-b border-dotted border-muted-foreground/25 mt-[0.4em]" />
                    <span className="font-mono text-sm font-medium shrink-0 tabular-nums">
                      {typeof value === 'number' ? value.toLocaleString() : String(value)}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
