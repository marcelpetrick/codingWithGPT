import { sharedSymbols } from './deck'
import type { Card, GamePhase, SymbolId } from './types'

export interface GameRun {
  readonly cards: readonly Card[]
  readonly phase: Extract<
    GamePhase,
    'active' | 'transitioning' | 'completed' | 'abandoned'
  >
  readonly currentIndex: number
  readonly incorrectSelections: number
}

export type SelectionResult = 'correct' | 'incorrect' | 'ignored'

export function createGameRun(cards: readonly Card[]): GameRun {
  if (cards.length < 2) {
    throw new Error('A game requires at least two cards')
  }

  return {
    cards,
    phase: 'active',
    currentIndex: 0,
    incorrectSelections: 0,
  }
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
