import {
  canonicalDeck,
  cardCount,
  sharedSymbols,
  symbolCount,
  symbolsPerCard,
} from './deck'

describe('canonical projective-plane deck', () => {
  it('contains 57 cards with eight unique valid symbols each', () => {
    expect(canonicalDeck).toHaveLength(cardCount)

    canonicalDeck.forEach((card, index) => {
      expect(card.id).toBe(index)
      expect(card.symbolIds).toHaveLength(symbolsPerCard)
      expect(new Set(card.symbolIds).size).toBe(symbolsPerCard)
      card.symbolIds.forEach((symbolId) => {
        expect(symbolId).toBeGreaterThanOrEqual(0)
        expect(symbolId).toBeLessThan(symbolCount)
      })
    })
  })

  it('uses every symbol on exactly eight cards', () => {
    const occurrences = Array.from({ length: symbolCount }, () => 0)

    canonicalDeck.forEach((card) => {
      card.symbolIds.forEach((symbolId) => {
        occurrences[symbolId] += 1
      })
    })

    expect(occurrences).toEqual(Array.from({ length: symbolCount }, () => 8))
  })

  it('gives every pair of distinct cards exactly one shared symbol', () => {
    for (let first = 0; first < canonicalDeck.length; first += 1) {
      for (let second = first + 1; second < canonicalDeck.length; second += 1) {
        expect(
          sharedSymbols(canonicalDeck[first], canonicalDeck[second]),
        ).toHaveLength(1)
      }
    }
  })
})
