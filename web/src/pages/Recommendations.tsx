import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRecommendations, updateRecommendation, RecommendationItem } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SeverityBadge } from '@/components/SeverityBadge'
import { Button } from '@/components/ui/button'
import { Lightbulb, Loader2, Check, X } from 'lucide-react'

export function RecommendationsPage() {
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editNotes, setEditNotes] = useState('')

  const { data: recData, isLoading } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => getRecommendations().then((r) => r.data),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status, notes }: { id: number; status: string; notes?: string }) =>
      updateRecommendation(id, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
      setEditingId(null)
      setEditNotes('')
    },
  })

  const recommendations = recData?.recommendations ?? []
  const summary = recData?.summary ?? { total: 0, open: 0, applied: 0, dismissed: 0 }

  const grouped = {
    open: recommendations.filter((r) => r.status === 'open'),
    applied: recommendations.filter((r) => r.status === 'applied'),
    dismissed: recommendations.filter((r) => r.status === 'dismissed'),
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Recommendations</h1>
        <p className="text-muted-foreground">Track and manage optimization suggestions</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold">{summary.total}</div>
              <div className="text-sm text-muted-foreground">Total</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-sky-500">{summary.open}</div>
              <div className="text-sm text-muted-foreground">Open</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald-500">{summary.applied}</div>
              <div className="text-sm text-muted-foreground">Applied</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-500">{summary.dismissed}</div>
              <div className="text-sm text-muted-foreground">Dismissed</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-3">
          {(['open', 'applied', 'dismissed'] as const).map((status) => (
            <Card key={status}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <SeverityBadge severity={status} />
                  {status.charAt(0).toUpperCase() + status.slice(1)} ({grouped[status].length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {grouped[status].map((rec) => (
                  <Card key={rec.id} className="border-muted">
                    <CardContent className="pt-4">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <Lightbulb className="h-4 w-4 text-amber-500" />
                            <span className="font-medium">{rec.title}</span>
                          </div>
                          <p className="mt-1 text-sm text-muted-foreground">{rec.description}</p>
                          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                            <SeverityBadge severity={rec.category} />
                            <span>{new Date(rec.created_at).toLocaleDateString()}</span>
                          </div>
                          {rec.notes && (
                            <p className="mt-2 text-xs italic text-muted-foreground">{rec.notes}</p>
                          )}
                        </div>
                        {status === 'open' && (
                          <div className="flex flex-col gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0 text-emerald-500"
                              onClick={() => {
                                setEditingId(rec.id)
                                updateMutation.mutate({ id: rec.id, status: 'applied' })
                              }}
                            >
                              <Check className="h-3 w-3" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0 text-gray-500"
                              onClick={() => {
                                setEditingId(rec.id)
                                updateMutation.mutate({ id: rec.id, status: 'dismissed' })
                              }}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {grouped[status].length === 0 && (
                  <p className="py-4 text-center text-sm text-muted-foreground">None</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
