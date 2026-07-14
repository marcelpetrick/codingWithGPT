import { emptyRankings, type TieredRankings } from './rankings'
import { isChallengeSize, type Preferences, type RankingEntry } from './types'

export const storageKey = 'recognizer-game:v1'

export interface StorageLike {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export interface StoredGameData {
  readonly version: 1
  readonly preferences: Preferences
  readonly rankings: TieredRankings
  readonly nextInsertionOrder: number
}

export const defaultPreferences: Preferences = {
  playerName: '',
  challengeSize: 10,
  soundEnabled: false,
  reducedMotion: false,
}

export function defaultGameData(): StoredGameData {
  return {
    version: 1,
    preferences: defaultPreferences,
    rankings: emptyRankings(),
    nextInsertionOrder: 0,
  }
}

function isRankingEntry(value: unknown): value is RankingEntry {
  if (!value || typeof value !== 'object') {
    return false
  }
  const entry = value as Record<string, unknown>
  return (
    typeof entry.id === 'string' &&
    typeof entry.playerName === 'string' &&
    typeof entry.elapsedMs === 'number' &&
    Number.isFinite(entry.elapsedMs) &&
    typeof entry.completedAt === 'number' &&
    Number.isFinite(entry.completedAt) &&
    typeof entry.insertionOrder === 'number' &&
    Number.isFinite(entry.insertionOrder) &&
    typeof entry.challengeSize === 'number' &&
    isChallengeSize(entry.challengeSize)
  )
}

function isPreferences(value: unknown): value is Preferences {
  if (!value || typeof value !== 'object') {
    return false
  }
  const preferences = value as Record<string, unknown>
  return (
    typeof preferences.playerName === 'string' &&
    typeof preferences.challengeSize === 'number' &&
    isChallengeSize(preferences.challengeSize) &&
    typeof preferences.soundEnabled === 'boolean' &&
    typeof preferences.reducedMotion === 'boolean'
  )
}

function parseRankings(value: unknown): TieredRankings | undefined {
  if (!value || typeof value !== 'object') {
    return undefined
  }

  const rankingRecord = value as Record<string, unknown>
  const rankings = emptyRankings()
  for (const tier of [10, 20, 50] as const) {
    const entries = rankingRecord[tier]
    if (!Array.isArray(entries) || !entries.every(isRankingEntry)) {
      return undefined
    }
    rankings[tier] = entries
      .filter((entry) => entry.challengeSize === tier)
      .sort(
        (first, second) =>
          first.elapsedMs - second.elapsedMs ||
          first.insertionOrder - second.insertionOrder,
      )
      .slice(0, 10)
  }
  return rankings
}

export function parseGameData(value: unknown): StoredGameData | undefined {
  if (!value || typeof value !== 'object') {
    return undefined
  }
  const data = value as Record<string, unknown>
  const rankings = parseRankings(data.rankings)
  if (
    data.version !== 1 ||
    !isPreferences(data.preferences) ||
    !rankings ||
    typeof data.nextInsertionOrder !== 'number' ||
    !Number.isSafeInteger(data.nextInsertionOrder) ||
    data.nextInsertionOrder < 0
  ) {
    return undefined
  }

  return {
    version: 1,
    preferences: data.preferences,
    rankings,
    nextInsertionOrder: data.nextInsertionOrder,
  }
}

export function loadGameData(storage?: StorageLike): StoredGameData {
  if (!storage) {
    return defaultGameData()
  }
  try {
    const raw = storage.getItem(storageKey)
    return raw
      ? (parseGameData(JSON.parse(raw)) ?? defaultGameData())
      : defaultGameData()
  } catch {
    return defaultGameData()
  }
}

export function saveGameData(
  storage: StorageLike | undefined,
  data: StoredGameData,
): boolean {
  if (!storage) {
    return false
  }
  try {
    storage.setItem(storageKey, JSON.stringify(data))
    return true
  } catch {
    return false
  }
}

export function clearGameData(storage?: StorageLike): boolean {
  if (!storage) {
    return false
  }
  try {
    storage.removeItem(storageKey)
    return true
  } catch {
    return false
  }
}
