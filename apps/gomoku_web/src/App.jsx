import { useEffect, useMemo, useState } from 'react'

import { GomokuBoard } from './components/gomoku-board'
import { Badge } from './components/ui/badge'
import { Button } from './components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { ScrollArea } from './components/ui/scroll-area'
import { Separator } from './components/ui/separator'
import { buildBoardSnapshot, buildReplayModel } from './lib/replay'

function App() {
  const [payload, setPayload] = useState({
    state: {},
    events: [],
    live_logs: { B: [], W: [] },
    runtime_status: 'idle',
    model: 'gpt-5.3-codex',
    match_running: false,
    mcp_ready: false,
    mcp_error: '',
  })
  const [error, setError] = useState('')
  const [replayIndex, setReplayIndex] = useState(0)
  const [followLatest, setFollowLatest] = useState(true)
  const [speedMs, setSpeedMs] = useState(700)
  const [autoplay, setAutoplay] = useState(false)
  const [streamConnected, setStreamConnected] = useState(false)
  const [actionLoading, setActionLoading] = useState('')

  const state = payload.state || {}
  const runtimeStatus = String(payload.runtime_status || 'idle')
  const modelName = String(payload.model || 'gpt-5.3-codex')
  const codexAvailable = Boolean(payload.codex_available)
  const mcpReady = Boolean(payload.mcp_ready)
  const mcpError = String(payload.mcp_error || '')
  const matchRunning = Boolean(payload.match_running)
  const events = useMemo(() => (Array.isArray(payload.events) ? payload.events : []), [payload.events])
  const liveLogs = useMemo(() => {
    const raw = payload.live_logs || {}
    return {
      B: Array.isArray(raw.B) ? raw.B : [],
      W: Array.isArray(raw.W) ? raw.W : [],
    }
  }, [payload.live_logs])
  const history = useMemo(() => (Array.isArray(state.history) ? state.history : []), [state.history])
  const total = history.length
  const boardSize = Number(state.board_size) || 15

  const model = useMemo(() => buildReplayModel(events), [events])

  useEffect(() => {
    let disposed = false
    let reconnectTimer = null
    let source = null

    const applyPayload = (json) => {
      setPayload({
        state: json.state || {},
        events: json.events || [],
        live_logs: json.live_logs || { B: [], W: [] },
        runtime_status: json.runtime_status || 'idle',
        model: json.model || 'gpt-5.3-codex',
        codex_available: Boolean(json.codex_available),
        match_running: Boolean(json.match_running),
        mcp_ready: Boolean(json.mcp_ready),
        mcp_error: String(json.mcp_error || ''),
      })
    }

    const connect = () => {
      if (disposed) return
      source = new EventSource('/api/stream')
      source.addEventListener('state', (evt) => {
        try {
          const json = JSON.parse(evt.data)
          if (!json.ok) {
            throw new Error(json.error || 'stream payload error')
          }
          applyPayload(json)
          setStreamConnected(true)
          setError('')
        } catch (err) {
          setError(String(err))
        }
      })

      source.onerror = () => {
        setStreamConnected(false)
        if (source) {
          source.close()
        }
        if (!disposed) {
          reconnectTimer = window.setTimeout(connect, 1200)
        }
      }
    }

    connect()
    return () => {
      disposed = true
      if (source) {
        source.close()
      }
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer)
      }
    }
  }, [])

  useEffect(() => {
    if (followLatest) {
      setReplayIndex(total)
      setAutoplay(false)
    } else {
      setReplayIndex((prev) => Math.min(prev, total))
    }
  }, [total, followLatest])

  useEffect(() => {
    if (!autoplay) return undefined
    const timer = window.setInterval(() => {
      setReplayIndex((prev) => {
        const next = Math.min(prev + 1, total)
        if (next >= total) {
          setAutoplay(false)
          setFollowLatest(true)
        }
        return next
      })
    }, Math.max(200, speedMs))

    return () => window.clearInterval(timer)
  }, [autoplay, speedMs, total])

  const snapshot = useMemo(() => buildBoardSnapshot(boardSize, history, replayIndex), [boardSize, history, replayIndex])

  const stepStream = useMemo(() => {
    if (replayIndex <= 0 || replayIndex > total) {
      return ['Step 0: waiting for moves.']
    }
    const move = history[replayIndex - 1]
    const seq = Number(move.seq) || replayIndex
    const header = `Step ${seq}: ${move.player} (${move.row},${move.col}) src=${move.source}`
    const turn = model.turnBySeq.get(seq)
    if (!turn) {
      return [header, '[system] (thinking stream unavailable)']
    }
    return [header, ...turn.entries.map((entry) => `[${entry.kind}] ${entry.text}`)]
  }, [history, model.turnBySeq, replayIndex, total])

  const renderAgentLog = (player) => {
    const logs = model.agentLogs[player] || []
    const rows = []

    for (const item of logs) {
      if (item.seq == null) {
        if (replayIndex !== total) continue
        rows.push(`[live][${item.kind}] ${item.text}`)
        continue
      }
      if (item.seq > replayIndex) continue
      rows.push(`[${String(item.seq).padStart(3, '0')}][${item.kind}] ${item.text}`)
    }

    if (replayIndex === total) {
      for (const item of liveLogs[player] || []) {
        rows.push(`[live][${item.kind}] ${item.text}`)
      }
    }

    return rows.length ? rows : ['(no logs)']
  }

  const jumpTo = (index, follow = false) => {
    setAutoplay(false)
    setReplayIndex(Math.max(0, Math.min(index, total)))
    setFollowLatest(follow)
  }

  const postControl = async (path, body = {}, options = {}) => {
    setActionLoading(path)
    try {
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const json = await res.json()
      if (!res.ok || !json.ok) {
        throw new Error(json.error || 'request failed')
      }
      setPayload({
        state: json.state || {},
        events: json.events || [],
        live_logs: json.live_logs || { B: [], W: [] },
        runtime_status: json.runtime_status || 'idle',
        model: json.model || 'gpt-5.3-codex',
        codex_available: Boolean(json.codex_available),
        match_running: Boolean(json.match_running),
        mcp_ready: Boolean(json.mcp_ready),
        mcp_error: String(json.mcp_error || ''),
      })
      if (options.followLatest) {
        setFollowLatest(true)
      }
      setError('')
    } catch (err) {
      setError(String(err))
    } finally {
      setActionLoading('')
    }
  }

  const isLoading = (path) => actionLoading === path

  return (
    <div className="h-full p-3">
      <div className="grid h-full grid-rows-[auto_1fr] gap-3">
        <Card>
          <CardContent className="flex flex-wrap items-center gap-2 py-3">
            <Button
              size="sm"
              onClick={() => postControl('/api/match/start', { keep_memory: true }, { followLatest: true })}
              disabled={isLoading('/api/match/start') || !codexAvailable || !mcpReady || matchRunning}
            >
              Start
            </Button>
            <Button size="sm" variant="outline" onClick={() => postControl('/api/match/stop')} disabled={isLoading('/api/match/stop')}>
              Stop
            </Button>
            <Button size="sm" variant="outline" onClick={() => postControl('/api/match/reset', {}, { followLatest: true })} disabled={isLoading('/api/match/reset')}>
              Reset Board
            </Button>
            <Button size="sm" variant="outline" onClick={() => postControl('/api/match/clear-memory')} disabled={isLoading('/api/match/clear-memory')}>
              Clear Memory
            </Button>

            <Separator className="hidden sm:block sm:h-6 sm:w-px" />
            <Button size="sm" variant="outline" onClick={() => jumpTo(0, false)}>|&lt;</Button>
            <Button size="sm" variant="outline" onClick={() => jumpTo(replayIndex - 1, false)}>&lt;</Button>
            <Button size="sm" variant="outline" onClick={() => jumpTo(replayIndex + 1, false)}>&gt;</Button>
            <Button size="sm" variant="outline" onClick={() => jumpTo(total, true)}>&gt;|</Button>
            <Button
              size="sm"
              onClick={() => {
                if (!autoplay) {
                  setFollowLatest(false)
                }
                setAutoplay((prev) => !prev)
              }}
            >
              {autoplay ? 'Pause' : 'Auto Play'}
            </Button>

            <label className="ml-2 text-xs text-muted-foreground">
              speed(ms)
              <input
                type="number"
                min={200}
                max={3000}
                step={100}
                value={speedMs}
                onChange={(e) => setSpeedMs(Number(e.target.value) || 700)}
                className="ml-2 w-20 rounded-md border bg-card px-2 py-1 text-xs"
              />
            </label>

            <Separator className="hidden sm:block sm:h-6 sm:w-px" />
            <Badge>replay: {replayIndex}/{total} ({followLatest && replayIndex === total ? 'live' : 'replay'})</Badge>
            <Badge>{state.winner ? `winner: ${state.winner}` : `current: ${state.current_player || 'B'}`}</Badge>
            <Badge>runtime: {runtimeStatus}</Badge>
            <Badge>match: {matchRunning ? 'running' : 'stopped'}</Badge>
            <Badge>stream: {streamConnected ? 'connected' : 'reconnecting'}</Badge>
            <Badge>codex: {codexAvailable ? 'ready' : 'missing'}</Badge>
            <Badge>mcp: {mcpReady ? 'ready' : 'missing'}</Badge>
            <Badge>model: {modelName}</Badge>
            {!mcpReady && mcpError && <Badge className="border-amber-500 text-amber-700">mcp error: {mcpError}</Badge>}
            {error && <Badge className="border-red-500 text-red-700">{error}</Badge>}
          </CardContent>
        </Card>

        <div className="grid min-h-0 grid-cols-1 gap-3 xl:grid-cols-12">
          <Card className="min-h-0 xl:col-span-3">
            <CardHeader>
              <CardTitle>Agent B</CardTitle>
            </CardHeader>
            <CardContent className="h-[calc(100%-56px)] p-0">
              <ScrollArea className="h-full px-4 py-3">
                <pre className="code whitespace-pre-wrap">{renderAgentLog('B').join('\n')}</pre>
              </ScrollArea>
            </CardContent>
          </Card>

          <div className="grid min-h-0 grid-rows-[auto_auto_1fr] gap-3 xl:col-span-6">
            <Card>
              <CardHeader>
                <CardTitle>Board</CardTitle>
              </CardHeader>
              <CardContent className="pt-2">
                <GomokuBoard board={snapshot.board} history={snapshot.usedHistory} boardSize={boardSize} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Turn Records</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-28 px-4 py-3">
                  <pre className="code whitespace-pre-wrap">
                    {(history.length
                      ? history.map((move, idx) => {
                          const pointer = idx + 1 === replayIndex ? '>>' : '  '
                          const mark = idx + 1 <= replayIndex ? '*' : ' '
                          return `${pointer}${mark} ${String(move.seq ?? idx + 1).padStart(3, '0')} ${move.player} (${move.row},${move.col}) src=${move.source}`
                        })
                      : ['(no moves yet)']).join('\n')}
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>

            <Card className="min-h-0">
              <CardHeader>
                <CardTitle>Step Thinking Stream</CardTitle>
              </CardHeader>
              <CardContent className="h-[calc(100%-56px)] p-0">
                <ScrollArea className="h-full px-4 py-3">
                  <pre className="code whitespace-pre-wrap">{stepStream.join('\n')}</pre>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          <Card className="min-h-0 xl:col-span-3">
            <CardHeader>
              <CardTitle>Agent W</CardTitle>
            </CardHeader>
            <CardContent className="h-[calc(100%-56px)] p-0">
              <ScrollArea className="h-full px-4 py-3">
                <pre className="code whitespace-pre-wrap">{renderAgentLog('W').join('\n')}</pre>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default App
