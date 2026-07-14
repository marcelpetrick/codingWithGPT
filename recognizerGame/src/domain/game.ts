import { sharedSymbols } from './deck'
import { createSeededRandom } from './challenge'
import type { Card, GamePhase, SymbolId } from './types'

export interface GameRun {
  readonly cards: readonly Card[]
  readonly layoutSeeds: Readonly<Record<number, number>>
  readonly phase: Extract<
    GamePhase,
    'active' | 'transitioning' | 'completed' | 'abandoned'
  >
  readonly currentIndex: number
  readonly incorrectSelections: number
}

export type SelectionResult = 'correct' | 'incorrect' | 'ignored'

export function createGameRun(cards: readonly Card[], layoutSeed = 0): GameRun {
  if (cards.length < 2) {
    throw new Error('A game requires at least two cards')
  }

  const random = createSeededRandom(layoutSeed)
  const layoutSeeds = Object.fromEntries(
    cards.map((card) => [card.id, Math.floor(random() * 2_147_483_647)]),
  )

  return {
    cards,
    layoutSeeds,
    phase: 'active',
    currentIndex: 0,
    incorrectSelections: 0,
  }
}

export function cardLayoutSeed(run: GameRun, card: Card): number {
  const seed = run.layoutSeeds[card.id]
  if (seed === undefined) {
    throw new Error(`No layout seed exists for card ${card.id}`)
  }
  return seed
}

export function currentCard(run: GameRun): Card {
  return run.cards[run.currentIndex]
}

export function nextCard(run: GameRun): Card {
  return run.cards[run.currentIndex + 1]
}

export function currentMatch(run: GameRun): SymbolId {
  const match = sharedSymbols(currentCard(run), nextCard(run))
  if (match.length !== 1) {
    throw new Error('Visible cards must share exactly one symbol')
  }
  return match[0]
}

export function selectSymbol(
  run: GameRun,
  symbolId: SymbolId,
): { run: GameRun; result: SelectionResult } {
  if (run.phase !== 'active') {
    return { run, result: 'ignored' }
  }

  if (symbolId !== currentMatch(run)) {
    return {
      run: { ...run, incorrectSelections: run.incorrectSelections + 1 },
      result: 'incorrect',
    }
  }

  return { run: { ...run, phase: 'transitioning' }, result: 'correct' }
}

export function finishTransition(run: GameRun): GameRun {
  if (run.phase !== 'transitioning') {
    return run
  }

  if (run.currentIndex === run.cards.length - 2) {
    return { ...run, phase: 'completed' }
  }

  return {
    ...run,
    currentIndex: run.currentIndex + 1,
    phase: 'active',
  }
}

export function abandonGame(run: GameRun): GameRun {
  if (run.phase === 'completed') {
    return run
  }
  return { ...run, phase: 'abandoned' }
}

export function completedDecisionCount(run: GameRun): number {
  return run.currentIndex + (run.phase === 'completed' ? 1 : 0)
}
