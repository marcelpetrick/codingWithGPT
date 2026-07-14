import type { ChallengeSize, CompletedResult, RankingEntry } from './types'

export const rankingLimit = 10

export type TieredRankings = Record<ChallengeSize, readonly RankingEntry[]>

export const emptyRankings = (): TieredRankings => ({
  10: [],
  20: [],
  50: [],
})

function compareEntries(first: RankingEntry, second: RankingEntry): number {
  return (
    first.elapsedMs - second.elapsedMs ||
    first.insertionOrder - second.insertionOrder
  )
}

export function insertResult(
  rankings: TieredRankings,
  result: CompletedResult,
  insertionOrder: number,
): { rankings: TieredRankings; rank?: number; retained: boolean } {
  const entry: RankingEntry = { ...result, insertionOrder }
  const orderedTier = [...rankings[result.challengeSize], entry].sort(
    compareEntries,
  )
  const retainedTier = orderedTier.slice(0, rankingLimit)
  const rankIndex = retainedTier.findIndex((item) => item.id === result.id)

  return {
    rankings: { ...rankings, [result.challengeSize]: retainedTier },
    rank: rankIndex === -1 ? undefined : rankIndex + 1,
    retained: rankIndex !== -1,
  }
}

export function isPersonalBest(
  rankings: TieredRankings,
  result: CompletedResult,
): boolean {
  return !rankings[result.challengeSize]
    .filter((entry) => entry.playerName === result.playerName)
    .some((entry) => entry.elapsedMs < result.elapsedMs)
}
