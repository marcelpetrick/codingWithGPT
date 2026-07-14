import { createSeededRandom, shuffleCards } from './challenge'
import type { Card, SymbolId } from './types'

export interface SymbolPlacement {
  readonly symbolId: SymbolId
  readonly x: number
  readonly y: number
  readonly size: number
  readonly hitSize: number
  readonly rotation: number
}

const layoutSlots = [
  [50, 14],
  [75, 25],
  [86, 50],
  [75, 75],
  [50, 86],
  [25, 75],
  [14, 50],
  [25, 25],
] as const

export const layoutLimits = {
  minSize: 16,
  maxSize: 19,
  maxRotation: 18,
  hitSize: 20,
  safeEdge: 2,
} as const

export function createCardLayout(card: Card, seed: number): SymbolPlacement[] {
  const random = createSeededRandom(seed)
  const shuffledSymbols = shuffleCards(
    card.symbolIds.map((symbolId, id) => ({ id, symbolIds: [symbolId] })),
    random,
  ).map((cardEntry) => cardEntry.symbolIds[0])

  return shuffledSymbols.map((symbolId, index) => {
    const [baseX, baseY] = layoutSlots[index]
    const jitter = () => (random() - 0.5) * 2.5

    return {
      symbolId,
      x: baseX + jitter(),
      y: baseY + jitter(),
      size:
        layoutLimits.minSize +
        random() * (layoutLimits.maxSize - layoutLimits.minSize),
      hitSize: layoutLimits.hitSize,
      rotation: (random() - 0.5) * 2 * layoutLimits.maxRotation,
    }
  })
}
