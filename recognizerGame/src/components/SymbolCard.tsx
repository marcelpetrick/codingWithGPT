import type { CSSProperties } from 'react'
import { SymbolMark } from './SymbolMark'
import { createCardLayout } from '../domain/layout'
import { getSymbolMetadata } from '../domain/symbols'
import type { Card, SymbolId } from '../domain/types'

interface SymbolCardProps {
  readonly card: Card
  readonly label: string
  readonly seed: number
  readonly selectedSymbolId?: SymbolId
  readonly disabled?: boolean
  readonly onSelect: (symbolId: SymbolId) => void
}

export function SymbolCard({
  card,
  label,
  seed,
  selectedSymbolId,
  disabled = false,
  onSelect,
}: SymbolCardProps) {
  const placements = createCardLayout(card, seed)

  return (
    <section className="symbol-card-wrap" aria-label={label}>
      <p className="card-label">{label}</p>
      <div className="symbol-card">
        {placements.map((placement) => {
          const symbol = getSymbolMetadata(placement.symbolId)
          const isSelected = selectedSymbolId === placement.symbolId

          return (
            <button
              key={placement.symbolId}
              type="button"
              className={`symbol-button${isSelected ? ' is-selected' : ''}`}
              style={
                {
                  '--symbol-x': `${placement.x}%`,
                  '--symbol-y': `${placement.y}%`,
                  '--symbol-size': `${placement.size}%`,
                  '--symbol-rotation': `${placement.rotation}deg`,
                  '--symbol-color': symbol.color,
                } as CSSProperties
              }
              aria-label={`Select ${symbol.label}`}
              disabled={disabled}
              onClick={() => onSelect(placement.symbolId)}
            >
              <SymbolMark symbol={symbol} />
            </button>
          )
        })}
      </div>
    </section>
  )
}
