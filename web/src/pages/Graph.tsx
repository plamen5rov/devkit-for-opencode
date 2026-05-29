import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Network } from 'vis-network/standalone'
import type { Node, Edge, Options } from 'vis-network/standalone'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { GraphNode, GraphEdge } from '@/lib/api'
import { getGraph, uploadConfig as uploadConfigApi } from '@/lib/api'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { vscodeDark } from '@uiw/codemirror-theme-vscode'
import { Loader2, Network as NetworkIcon, Upload } from 'lucide-react'

const SECTION_ORDER = ['config', 'model', 'agent', 'mcp', 'plugin', 'permission', 'instruction']

const DEMO_CONFIG = `{
  "model": "anthropic/claude-sonnet",
  "small_model": "anthropic/claude-haiku",
  "permission": {
    "*": "ask",
    "edit": "allow",
    "bash": {
      "*": "ask",
      "git *": "allow"
    }
  },
  "agent": {
    "build": { "disabled": false, "model": "anthropic/claude-sonnet" },
    "explore": { "disabled": true }
  },
  "mcp": {
    "sentry": { "type": "remote", "url": "https://mcp.sentry.dev/mcp", "enabled": true }
  },
  "plugin": ["opencode-notifier@1.0.0"],
  "instructions": ["rules/COMMIT.md"]
}`

function groupByType(nodes: GraphNode[]): Record<string, GraphNode[]> {
  const groups: Record<string, GraphNode[]> = {}
  for (const n of nodes) {
    ;(groups[n.type] ??= []).push(n)
  }
  return groups
}

function StatsBar({ graph }: { graph: { nodes: GraphNode[]; edges: GraphEdge[] } }) {
  const groups = groupByType(graph.nodes)
  const sortedTypes = SECTION_ORDER.filter((t) => groups[t])

  return (
    <div className="flex flex-wrap gap-3">
      {sortedTypes.map((type) => (
        <div
          key={type}
          className="rounded-lg border px-3 py-1.5 text-sm"
          style={{ borderColor: groups[type][0].color + '40', backgroundColor: groups[type][0].color + '10' }}
        >
          <span className="font-medium" style={{ color: groups[type][0].color }}>
            {groups[type].length}
          </span>{' '}
          <span className="text-muted-foreground">{type}</span>
        </div>
      ))}
      <div className="rounded-lg border px-3 py-1.5 text-sm">
        <span className="font-medium">{graph.edges.length}</span>{' '}
        <span className="text-muted-foreground">edges</span>
      </div>
    </div>
  )
}

export function GraphPage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const [configContent, setConfigContent] = useState(DEMO_CONFIG)

  const graphMutation = useMutation({
    mutationFn: (content: string) => getGraph(content),
  })

  const handleAnalyze = useCallback(() => {
    graphMutation.mutate(configContent)
  }, [configContent, graphMutation.mutate])

  const handleUpload = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      try {
        const res = await uploadConfigApi(file)
        setConfigContent(res.data.content)
      } catch {
        // user cancelled or error
      }
    }
    input.click()
  }, [])

  useEffect(() => {
    if (!graphMutation.data?.data || !containerRef.current) return

    const { nodes: apiNodes, edges: apiEdges } = graphMutation.data.data

    if (networkRef.current) {
      networkRef.current.destroy()
    }

    const visNodes: Node[] = apiNodes.map((n) => ({
      id: n.id,
      label: n.label,
      color: {
        background: n.color,
        border: n.color,
        highlight: { background: n.color, border: n.color },
        hover: { background: n.color, border: n.color },
      },
      font: { color: '#fff', size: 12, face: 'monospace' },
      shape: 'box',
      margin: { top: 6, right: 10, bottom: 6, left: 10 },
      borderWidth: 0,
      widthConstraint: { maximum: 180 },
    }))

    const visEdges: Edge[] = apiEdges.map((e) => ({
      from: e.from,
      to: e.to,
      label: e.label,
      font: { size: 9, color: '#94a3b8', align: 'middle' as const },
      arrows: { to: { enabled: true, scaleFactor: 0.5 } },
      color: { color: '#475569', highlight: '#94a3b8' },
      smooth: { enabled: true, type: 'curvedCW', roundness: 0.15 },
    }))

    const options: Options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.005,
          springLength: 150,
          springConstant: 0.08,
        },
        stabilization: { iterations: 200 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true,
        navigationButtons: false,
      },
      layout: { improvedLayout: true },
    }

    const network = new Network(containerRef.current, { nodes: visNodes, edges: visEdges }, options)
    networkRef.current = network

    setTimeout(() => {
      network.stabilize(50)
    }, 100)

    return () => {
      network.destroy()
      networkRef.current = null
    }
  }, [graphMutation.data])

  const result = graphMutation.data?.data

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dependency Graph</h1>
        <p className="text-muted-foreground mt-1">
          Visualize relationships between models, agents, permissions, MCP servers, and plugins.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Config Input</CardTitle>
          <CardDescription>Paste an OpenCode config to generate a dependency graph.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <CodeMirror
            value={configContent}
            onChange={(val) => setConfigContent(val)}
            extensions={[json()]}
            theme={vscodeDark}
            height="250px"
            className="rounded-md overflow-hidden border"
          />
          <div className="flex gap-3">
            <Button onClick={handleAnalyze} disabled={graphMutation.isPending || !configContent.trim()}>
              {graphMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <NetworkIcon className="mr-2 h-4 w-4" />
              )}
              Generate Graph
            </Button>
            <Button variant="outline" onClick={handleUpload}>
              <Upload className="mr-2 h-4 w-4" />
              Upload Config
            </Button>
          </div>
        </CardContent>
      </Card>

      {graphMutation.isError && (
        <Card className="border-red-500/30 bg-red-500/5">
          <CardContent className="pt-6">
            <p className="text-red-600 dark:text-red-400">
              {(graphMutation.error as Error)?.message || 'Failed to generate graph'}
            </p>
          </CardContent>
        </Card>
      )}

      {result && (
        <>
          <StatsBar graph={result} />

          <Card>
            <CardContent className="pt-6">
              <div
                ref={containerRef}
                className="w-full rounded-md border"
                style={{ height: '500px', background: '#1e293b' }}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Legend</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Count</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(() => {
                    const groups = groupByType(result.nodes)
                    return SECTION_ORDER.filter((t) => groups[t]).map((type) => (
                      <TableRow key={type}>
                        <TableCell>
                          <span
                            className="inline-block w-3 h-3 rounded-sm mr-2"
                            style={{ backgroundColor: groups[type][0].color }}
                          />
                          {type}
                        </TableCell>
                        <TableCell>{groups[type].length}</TableCell>
                      </TableRow>
                    ))
                  })()}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Edge Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>From</TableHead>
                    <TableHead>Relation</TableHead>
                    <TableHead>To</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.edges.map((e, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-xs">{e.from}</TableCell>
                      <TableCell className="italic text-muted-foreground">{e.label}</TableCell>
                      <TableCell className="font-mono text-xs">{e.to}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
