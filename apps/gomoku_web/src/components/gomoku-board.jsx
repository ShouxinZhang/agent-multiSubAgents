import { useMemo } from 'react'

export function GomokuBoard({ board, history, boardSize }) {
  const size = Number(boardSize) || 15
  const px = 640
  const margin = 28
  const cell = (px - margin * 2) / (size - 1)

  const stones = useMemo(() => {
    const rows = []
    for (let r = 0; r < size; r += 1) {
      for (let c = 0; c < size; c += 1) {
        const token = board[r]?.[c]
        if (token === 'B' || token === 'W') {
          rows.push({ row: r, col: c, token })
        }
      }
    }
    return rows
  }, [board, size])

  const lastMove = history.length ? history[history.length - 1] : null

  return (
    <div className="rounded-md border border-[#b1935f] bg-[#d8b36e] p-2">
      <svg viewBox={`0 0 ${px} ${px}`} className="h-auto w-full max-w-[680px]">
        {Array.from({ length: size }).map((_, idx) => {
          const d = margin + idx * cell
          return (
            <g key={idx}>
              <line x1={margin} y1={d} x2={px - margin} y2={d} stroke="#5f4420" strokeWidth="1" />
              <line x1={d} y1={margin} x2={d} y2={px - margin} stroke="#5f4420" strokeWidth="1" />
            </g>
          )
        })}

        {stones.map((stone) => {
          const x = margin + stone.col * cell
          const y = margin + stone.row * cell
          return (
            <circle
              key={`${stone.row}-${stone.col}`}
              cx={x}
              cy={y}
              r={cell * 0.41}
              fill={stone.token === 'B' ? '#101214' : '#f8f8f3'}
              stroke={stone.token === 'B' ? '#e4ddd4' : '#0f1213'}
              strokeWidth="1.5"
            />
          )
        })}

        {lastMove && (
          <circle
            cx={margin + Number(lastMove.col) * cell}
            cy={margin + Number(lastMove.row) * cell}
            r={cell * 0.16}
            fill="none"
            stroke="#c81d25"
            strokeWidth="2"
          />
        )}
      </svg>
    </div>
  )
}
