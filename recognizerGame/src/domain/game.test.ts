import { createChallenge, createSeededRandom } from './challenge'
import {
  abandonGame,
  cardLayoutSeed,
  completedDecisionCount,
  createGameRun,
  currentMatch,
  finishTransition,
  selectSymbol,
} from './game'

describe('single-player game state', () => {
  it('advances exactly once for a correct symbol and accepts either card membership', () => {
    const run = createGameRun(createChallenge(10, createSeededRandom(5)))
    const match = currentMatch(run)
    expect(run.cards[0].symbolIds).toContain(match)
    expect(run.cards[1].symbolIds).toContain(match)

    const selected = selectSymbol(run, match)
    expect(selected.result).toBe('correct')
    expect(selected.run.phase).toBe('transitioning')
    expect(selectSymbol(selected.run, match).result).toBe('ignored')

    const advanced = finishTransition(selected.run)
    expect(advanced.currentIndex).toBe(1)
    expect(advanced.phase).toBe('active')
  })

  it('keeps each card layout seed stable while the run advances', () => {
    const run = createGameRun(createChallenge(10, createSeededRandom(4)), 77)
    const nextCard = run.cards[1]
    const nextSeed = cardLayoutSeed(run, nextCard)
    const advanced = finishTransition(selectSymbol(run, currentMatch(run)).run)

    expect(
      cardLayoutSeed(advanced, advanced.cards[advanced.currentIndex]),
    ).toBe(nextSeed)
    expect(createGameRun(run.cards, 77).layoutSeeds).toEqual(run.layoutSeeds)
  })

  it('keeps the pair active after a wrong selection', () => {
    const run = createGameRun(createChallenge(10, createSeededRandom(6)))
    const wrongSymbol = run.cards[0].symbolIds.find(
      (symbolId) => symbolId !== currentMatch(run),
    )!

    const selected = selectSymbol(run, wrongSymbol)
    expect(selected.result).toBe('incorrect')
    expect(selected.run.phase).toBe('active')
    expect(selected.run.currentIndex).toBe(0)
    expect(selected.run.incorrectSelections).toBe(1)
  })

  it('completes the final matching decision', () => {
    let run = createGameRun(createChallenge(10, createSeededRandom(8)))

    while (run.phase === 'active') {
      run = finishTransition(selectSymbol(run, currentMatch(run)).run)
    }

    expect(run.phase).toBe('completed')
    expect(completedDecisionCount(run)).toBe(9)
    expect(selectSymbol(run, currentMatch(run)).result).toBe('ignored')
  })

  it('abandons incomplete games without changing completed games', () => {
    const run = createGameRun(createChallenge(10, createSeededRandom(9)))
    expect(abandonGame(run).phase).toBe('abandoned')

    const completed = {
      ...run,
      phase: 'completed' as const,
    }
    expect(abandonGame(completed)).toEqual(completed)
  })
})
