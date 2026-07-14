import { canonicalDeck } from './deck'
import type { Card, ChallengeSize } from './types'

export type RandomSource = () => number

/** A small deterministic random source for replayable layouts and tests. */
export function createSeededRandom(seed: number): RandomSource {
  let state = seed >>> 0

  return () => {
    state += 0x6d2b79f5
    let value = state
    value = Math.imul(value ^ (value >>> 15), value | 1)
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61)
    return ((value ^ (value >>> 14)) >>> 0) / 4_294_967_296
  }
}

export function shuffleCards(
  cards: readonly Card[],
  random: RandomSource = Math.random,
): Card[] {
  const shuffled = [...cards]

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1))
    ;[shuffled[index], shuffled[swapIndex]] = [
      shuffled[swapIndex],
      shuffled[index],
    ]
  }

  return shuffled
}

export function createChallenge(
  challengeSize: ChallengeSize,
  random: RandomSource = Math.random,
): Card[] {
  return shuffleCards(canonicalDeck, random).slice(0, challengeSize)
}
