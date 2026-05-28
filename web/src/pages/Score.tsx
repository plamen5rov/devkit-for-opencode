import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { getScore } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScoreGauge } from '@/components/ScoreGauge'
import { Loader2, ChevronDown, ChevronRight } from 'lucide-react'

export function ScorePage() {
  const [configPath, setConfigPath] = useState('')
  const [detailed, setDetailed] = useState(true)

  const scoreMutation = useMutation({
    mutationFn: ({ path, detailed }: { path?: string; detailed: boolean }) =>
      getScore(path, detailed),
  })

  const handleRun = () => {
    scoreMutation.mutate({ path: configPath || undefined, detailed })
  }

  const result = scoreMutation.data?.data
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
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="~/.config/opencode/opencode.json"
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm"
              value={configPath}
              onChange={(e) => setConfigPath(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={detailed}
                onChange={(e) => setDetailed(e.target.checked)}
              />
              Detailed
            </label>
          </div>
          <Button onClick={handleRun} disabled={scoreMutation.isPending}>
            {scoreMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Calculate Score
          </Button>
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          <div className="flex justify-center">
            <ScoreGauge score={result.health_score} label="Health Score" size={160} />
          </div>

          {breakdown && (
            <Card>
              <CardHeader>
                <CardTitle>Factor Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {Object.entries(breakdown).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-sm capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="font-mono text-sm font-medium">
                      {typeof value === 'number' ? value.toLocaleString() : String(value)}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {result.summary && (
            <Card>
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {Object.entries(result.summary).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-sm capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="font-mono text-sm font-medium">
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
