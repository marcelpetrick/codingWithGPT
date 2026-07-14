import type { SymbolMetadata } from '../domain/symbols'
import { symbolIcons } from './symbolIcons'

interface SymbolMarkProps {
  readonly symbol: SymbolMetadata
}

export function SymbolMark({ symbol }: SymbolMarkProps) {
  const Icon = symbolIcons[symbol.name]
  if (!Icon) {
    throw new Error(`No icon is mapped for ${symbol.name}`)
  }

  return (
    <Icon
      aria-hidden="true"
      className="symbol-mark"
      fill={symbol.color}
      stroke="#172033"
      strokeWidth={2.8}
    />
  )
}
