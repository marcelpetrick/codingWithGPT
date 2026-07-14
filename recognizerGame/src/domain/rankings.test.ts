import {
  emptyRankings,
  insertResult,
  isPersonalBest,
  rankingLimit,
} from './rankings'
import type { CompletedResult } from './types'

function result(
  id: string,
  elapsedMs: number,
  challengeSize: 10 | 20 | 50 = 10,
  playerName = 'Player',
): CompletedResult {
  return { id, elapsedMs, challengeSize, playerName, completedAt: 1 }
}

describe('tiered rankings', () => {
  it('orders lower times first and keeps tiers separate', () => {
    const first = insertResult(emptyRankings(), result('slow', 5_000), 1)
    const second = insertResult(first.rankings, result('fast', 3_000), 2)
    const third = insertResult(second.rankings, result('medium', 4_000, 20), 3)

    expect(third.rankings[10].map((entry) => entry.id)).toEqual([
      'fast',
      'slow',
    ])
    expect(third.rankings[20].map((entry) => entry.id)).toEqual(['medium'])
    expect(third.rank).toBe(1)
  })

  it('keeps equal times in first-completed order', () => {
    const first = insertResult(emptyRankings(), result('first', 3_000), 1)
    const second = insertResult(first.rankings, result('second', 3_000), 2)

    expect(second.rankings[10].map((entry) => entry.id)).toEqual([
      'first',
      'second',
    ])
  })

  it('retains only the best ten entries', () => {
    let rankings = emptyRankings()
    for (let index = 0; index < rankingLimit; index += 1) {
      rankings = insertResult(
        rankings,
        result(String(index), 1_000 + index),
        index,
      ).rankings
    }

    const outside = insertResult(rankings, result('outside', 9_999), 99)
    const winner = insertResult(rankings, result('winner', 500), 100)

    expect(outside.retained).toBe(false)
    expect(winner.rank).toBe(1)
    expect(winner.rankings[10]).toHaveLength(rankingLimit)
    expect(winner.rankings[10].at(-1)?.id).toBe('8')
  })

  it('calculates personal bests by exact name and challenge tier', () => {
    const rankings = insertResult(
      emptyRankings(),
      result('earlier', 3_000, 10, 'Ana'),
      1,
    ).rankings

    expect(isPersonalBest(rankings, result('better', 2_000, 10, 'Ana'))).toBe(
      true,
    )
    expect(isPersonalBest(rankings, result('slower', 4_000, 10, 'Ana'))).toBe(
      false,
    )
    expect(
      isPersonalBest(rankings, result('other-tier', 4_000, 20, 'Ana')),
    ).toBe(true)
  })
})
