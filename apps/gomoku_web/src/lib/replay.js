function toInt(value) {
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

export function buildReplayModel(events = []) {
  const turnsByKey = new Map()
  const turnBySeq = new Map()
  const agentLogs = { B: [], W: [] }
  let nextTurnId = 1

  for (const raw of events) {
    if (!raw || typeof raw !== 'object') {
      continue
    }

    const player = String(raw.player ?? '').toUpperCase()
    if (player !== 'B' && player !== 'W') {
      continue
    }

    let turnId = toInt(raw.turn_id)
    if (!turnId || turnId <= 0) {
      turnId = nextTurnId
    }
    nextTurnId = Math.max(nextTurnId, turnId + 1)

    const seq = toInt(raw.seq)
    const key = `${player}:${turnId}`

    let turn = turnsByKey.get(key)
    if (!turn) {
      turn = { id: turnId, player, seq, entries: [] }
      turnsByKey.set(key, turn)
    } else if (turn.seq == null && seq != null) {
      turn.seq = seq
    }

    const entry = {
      player,
      kind: String(raw.kind ?? 'log'),
      text: String(raw.text ?? ''),
      seq,
      turnId,
      order: toInt(raw.order) ?? turn.entries.length + 1,
    }

    turn.entries.push(entry)
    agentLogs[player].push(entry)

    if (seq != null && !turnBySeq.has(seq)) {
      turnBySeq.set(seq, turn)
    }
  }

  for (const player of ['B', 'W']) {
    agentLogs[player].sort((a, b) => {
      if (a.seq == null && b.seq == null) return a.order - b.order
      if (a.seq == null) return 1
      if (b.seq == null) return -1
      if (a.seq !== b.seq) return a.seq - b.seq
      return a.order - b.order
    })
  }

  return { turnBySeq, agentLogs }
}

export function buildBoardSnapshot(boardSize, history, replayIndex) {
  const size = Number(boardSize) || 15
  const board = Array.from({ length: size }, () => Array.from({ length: size }, () => '.'))
  const usedHistory = history.slice(0, replayIndex)

  for (const move of usedHistory) {
    const row = Number(move.row)
    const col = Number(move.col)
    const player = String(move.player ?? '.').toUpperCase()
    if ((player === 'B' || player === 'W') && row >= 0 && row < size && col >= 0 && col < size) {
      board[row][col] = player
    }
  }

  return { board, usedHistory }
}
