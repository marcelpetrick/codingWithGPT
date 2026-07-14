import { canonicalDeck } from './deck'
import { createChallenge, createSeededRandom, shuffleCards } from './challenge'

describe('challenge selection', () => {
  it.each([10, 20, 50] as const)(
    'selects %s distinct cards',
    (challengeSize) => {
      const challenge = createChallenge(challengeSize, createSeededRandom(42))

      expect(challenge).toHaveLength(challengeSize)
      expect(new Set(challenge.map((card) => card.id)).size).toBe(challengeSize)
    },
  )

  it('is reproducible from a seed without changing the canonical deck', () => {
    const before = canonicalDeck.map((card) => card.id)
    const first = createChallenge(20, createSeededRandom(7)).map(
      (card) => card.id,
    )
    const second = createChallenge(20, createSeededRandom(7)).map(
      (card) => card.id,
    )

    expect(first).toEqual(second)
    expect(canonicalDeck.map((card) => card.id)).toEqual(before)
  })

  it('returns a new shuffled array', () => {
    const cards = canonicalDeck.slice(0, 4)
    const shuffled = shuffleCards(cards, createSeededRandom(1))

    expect(shuffled).not.toBe(cards)
    expect(new Set(shuffled.map((card) => card.id))).toEqual(
      new Set(cards.map((card) => card.id)),
    )
  })
})
