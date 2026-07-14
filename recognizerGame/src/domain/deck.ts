import type { Card, SymbolId } from './types'

export const fieldOrder = 7
export const symbolCount = fieldOrder * fieldOrder + fieldOrder + 1
export const cardCount = symbolCount
export const symbolsPerCard = fieldOrder + 1

function affinePoint(x: number, y: number): SymbolId {
  return y * fieldOrder + x
}

function slopeInfinityPoint(slope: number): SymbolId {
  return fieldOrder * fieldOrder + slope
}

const verticalInfinityPoint = symbolCount - 1

function modulo(value: number): number {
  return ((value % fieldOrder) + fieldOrder) % fieldOrder
}

/**
 * Builds the lines of the projective plane over the field with seven elements.
 * Lines are cards and points are symbol IDs. This construction guarantees that
 * each pair of distinct lines intersects in exactly one point.
 */
export function createCanonicalDeck(): readonly Card[] {
  const cards: Card[] = []

  for (let slope = 0; slope < fieldOrder; slope += 1) {
    for (let intercept = 0; intercept < fieldOrder; intercept += 1) {
      const symbolIds = Array.from({ length: fieldOrder }, (_, x) =>
        affinePoint(x, modulo(slope * x + intercept)),
      )
      symbolIds.push(slopeInfinityPoint(slope))
      cards.push({ id: cards.length, symbolIds })
    }
  }

  for (let x = 0; x < fieldOrder; x += 1) {
    const symbolIds = Array.from({ length: fieldOrder }, (_, y) =>
      affinePoint(x, y),
    )
    symbolIds.push(verticalInfinityPoint)
    cards.push({ id: cards.length, symbolIds })
  }

  cards.push({
    id: cards.length,
    symbolIds: Array.from({ length: symbolsPerCard }, (_, point) =>
      point < fieldOrder ? slopeInfinityPoint(point) : verticalInfinityPoint,
    ),
  })

  return cards
}

export const canonicalDeck = createCanonicalDeck()

export function sharedSymbols(first: Card, second: Card): readonly SymbolId[] {
  const firstSymbols = new Set(first.symbolIds)
  return second.symbolIds.filter((symbolId) => firstSymbols.has(symbolId))
}
