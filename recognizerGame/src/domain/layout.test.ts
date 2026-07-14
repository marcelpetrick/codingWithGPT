import { canonicalDeck } from './deck'
import { createCardLayout, layoutLimits } from './layout'

function overlaps(
  first: { x: number; y: number; size: number },
  second: { x: number; y: number; size: number },
): boolean {
  const distance = Math.hypot(first.x - second.x, first.y - second.y)
  return distance < (first.size + second.size) / 2
}

describe('card layout', () => {
  it('is deterministic and preserves all card symbols', () => {
    const card = canonicalDeck[0]
    const first = createCardLayout(card, 42)
    const second = createCardLayout(card, 42)

    expect(first).toEqual(second)
    expect(
      first.map((placement) => placement.symbolId).sort((a, b) => a - b),
    ).toEqual([...card.symbolIds].sort((a, b) => a - b))
  })

  it('keeps symbols separate, inside the card, and within visual limits', () => {
    canonicalDeck.slice(0, 20).forEach((card) => {
      for (let seed = 0; seed < 50; seed += 1) {
        const placements = createCardLayout(card, seed)

        expect(placements).toHaveLength(8)
        placements.forEach((placement) => {
          const halfSize = placement.size / 2
          expect(placement.size).toBeGreaterThanOrEqual(layoutLimits.minSize)
          expect(placement.size).toBeLessThanOrEqual(layoutLimits.maxSize)
          expect(placement.hitSize).toBe(layoutLimits.hitSize)
          expect(Math.abs(placement.rotation)).toBeLessThanOrEqual(
            layoutLimits.maxRotation,
          )
          expect(placement.x - halfSize).toBeGreaterThanOrEqual(
            layoutLimits.safeEdge,
          )
          expect(placement.x + halfSize).toBeLessThanOrEqual(
            100 - layoutLimits.safeEdge,
          )
          expect(placement.y - halfSize).toBeGreaterThanOrEqual(
            layoutLimits.safeEdge,
          )
          expect(placement.y + halfSize).toBeLessThanOrEqual(
            100 - layoutLimits.safeEdge,
          )
        })

        placements.forEach((placement, index) => {
          placements.slice(index + 1).forEach((other) => {
            expect(overlaps(placement, other)).toBe(false)
            expect(
              overlaps(
                { ...placement, size: placement.hitSize },
                { ...other, size: other.hitSize },
              ),
            ).toBe(false)
          })
        })
      }
    })
  })
})
