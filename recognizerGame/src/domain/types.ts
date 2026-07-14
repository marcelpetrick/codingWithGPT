export const challengeSizes = [10, 20, 50] as const

export type ChallengeSize = (typeof challengeSizes)[number]

export type SymbolId = number

export interface Card {
  readonly id: number
  readonly symbolIds: readonly SymbolId[]
}

export type GamePhase =
  | 'menu'
  | 'help'
  | 'preparing'
  | 'active'
  | 'transitioning'
  | 'completed'
  | 'abandoned'

export interface CompletedResult {
  readonly id: string
  readonly playerName: string
  readonly challengeSize: ChallengeSize
  readonly elapsedMs: number
  readonly completedAt: number
}

export interface RankingEntry extends CompletedResult {
  readonly insertionOrder: number
}

export interface Preferences {
  readonly playerName: string
  readonly challengeSize: ChallengeSize
  readonly soundEnabled: boolean
  readonly reducedMotion: boolean
}

export function isChallengeSize(value: number): value is ChallengeSize {
  return challengeSizes.includes(value as ChallengeSize)
}

export function matchingDecisionCount(challengeSize: ChallengeSize): number {
  return challengeSize - 1
}
