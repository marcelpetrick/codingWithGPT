import { useEffect, useMemo, useState } from 'react'
import { SymbolCard } from './components/SymbolCard'
import { createChallenge } from './domain/challenge'
import {
  completedDecisionCount,
  createGameRun,
  currentMatch,
  finishTransition,
  selectSymbol,
  type GameRun,
} from './domain/game'
import {
  elapsedMilliseconds,
  finishTimer,
  formatDuration,
  startTimer,
  type RunTimer,
} from './domain/timer'
import {
  challengeSizes,
  matchingDecisionCount,
  type ChallengeSize,
  type SymbolId,
} from './domain/types'

type View = 'menu' | 'help' | 'game' | 'results'

const defaultChallengeSize: ChallengeSize = 10

function displayName(name: string): string {
  return name.trim() || 'Player'
}

export function App() {
  const [view, setView] = useState<View>('menu')
  const [playerName, setPlayerName] = useState('')
  const [challengeSize, setChallengeSize] =
    useState<ChallengeSize>(defaultChallengeSize)
  const [run, setRun] = useState<GameRun | null>(null)
  const [timer, setTimer] = useState<RunTimer | null>(null)
  const [now, setNow] = useState(0)
  const [selectedSymbolId, setSelectedSymbolId] = useState<SymbolId>()
  const [warning, setWarning] = useState('')

  const elapsed = timer ? elapsedMilliseconds(timer, now) : 0
  const decisionCount = matchingDecisionCount(challengeSize)

  useEffect(() => {
    if (view !== 'game' || !timer || run?.phase === 'completed') {
      return undefined
    }

    const intervalId = window.setInterval(() => setNow(Date.now()), 100)
    return () => window.clearInterval(intervalId)
  }, [run?.phase, timer, view])

  const sharedSymbol = useMemo(
    () => (run && run.phase !== 'completed' ? currentMatch(run) : undefined),
    [run],
  )

  function startGame() {
    const newRun = createGameRun(createChallenge(challengeSize))
    const startedAt = Date.now()
    setRun(newRun)
    setTimer(startTimer(startedAt))
    setNow(startedAt)
    setSelectedSymbolId(undefined)
    setWarning('')
    setView('game')
  }

  function handleSelection(symbolId: SymbolId) {
    if (!run || !timer) {
      return
    }

    const selection = selectSymbol(run, symbolId)
    setRun(selection.run)

    if (selection.result === 'incorrect') {
      setWarning('Not the shared symbol — keep looking!')
      return
    }

    if (selection.result !== 'correct') {
      return
    }

    setWarning('')
    setSelectedSymbolId(symbolId)
    window.setTimeout(() => {
      const nextRun = finishTransition(selection.run)
      setRun(nextRun)
      setSelectedSymbolId(undefined)

      if (nextRun.phase === 'completed') {
        const finishedTimer = finishTimer(timer, Date.now())
        setTimer(finishedTimer)
        setNow(finishedTimer.finishedAt ?? Date.now())
        setView('results')
      }
    }, 240)
  }

  if (view === 'help') {
    return (
      <main className="app-shell">
        <section className="panel help-panel">
          <p className="eyebrow">How to play</p>
          <h1>Find the one match</h1>
          <ol>
            <li>Two cards appear with eight symbols each.</li>
            <li>They share exactly one symbol.</li>
            <li>Click that symbol on either card.</li>
            <li>
              The right card becomes your new card and a new card appears.
            </li>
            <li>Finish every pair as quickly as you can.</li>
          </ol>
          <p>
            The clock runs continuously. Wrong picks only show a small warning,
            so you can keep trying.
          </p>
          <button
            className="button"
            type="button"
            onClick={() => setView('menu')}
          >
            Back to menu
          </button>
        </section>
      </main>
    )
  }

  if (view === 'results' && run && timer) {
    return (
      <main className="app-shell">
        <section className="panel results-panel">
          <p className="eyebrow">Challenge complete</p>
          <h1>Nice work, {displayName(playerName)}!</h1>
          <p className="result-time" aria-label="Final time">
            {formatDuration(
              elapsedMilliseconds(timer, timer.finishedAt ?? now),
              true,
            )}
          </p>
          <p>
            {challengeSize} cards · {run.incorrectSelections} wrong pick
            {run.incorrectSelections === 1 ? '' : 's'}
          </p>
          <div className="button-row">
            <button className="button" type="button" onClick={startGame}>
              Play again
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => setView('menu')}
            >
              Main menu
            </button>
          </div>
        </section>
      </main>
    )
  }

  if (view === 'game' && run && timer && sharedSymbol !== undefined) {
    const completed = completedDecisionCount(run)
    return (
      <main className="game-shell">
        <header className="game-header">
          <div>
            <p className="eyebrow">Recognizer</p>
            <p className="progress-text">
              {completed} of {decisionCount} matches
            </p>
          </div>
          <div className="timer" aria-label="Elapsed time">
            {formatDuration(elapsed)}
          </div>
          <button
            className="text-button"
            type="button"
            onClick={() => {
              if (
                window.confirm(
                  'Leave this challenge? Your current run will not be saved.',
                )
              ) {
                setView('menu')
                setRun(null)
                setTimer(null)
              }
            }}
          >
            Leave game
          </button>
        </header>
        <p className="game-instruction">
          Find the symbol that appears on both cards.
        </p>
        <p className="warning" role="status" aria-live="polite">
          {warning}
        </p>
        <section className="cards-grid" aria-label="Matching cards">
          <SymbolCard
            card={run.cards[run.currentIndex]}
            label="Your current card"
            seed={run.currentIndex * 2 + 1}
            selectedSymbolId={selectedSymbolId}
            disabled={run.phase !== 'active'}
            onSelect={handleSelection}
          />
          <SymbolCard
            card={run.cards[run.currentIndex + 1]}
            label="Next card"
            seed={run.currentIndex * 2 + 2}
            selectedSymbolId={selectedSymbolId}
            disabled={run.phase !== 'active'}
            onSelect={handleSelection}
          />
        </section>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <section className="panel menu-panel">
        <p className="eyebrow">Visual concentration</p>
        <h1>Recognizer</h1>
        <p className="intro">
          Find the one symbol shared by both cards — fast.
        </p>
        <label className="field-label" htmlFor="player-name">
          Your name <span>(optional)</span>
        </label>
        <input
          id="player-name"
          className="name-input"
          value={playerName}
          maxLength={24}
          autoComplete="nickname"
          placeholder="Player"
          onChange={(event) => setPlayerName(event.target.value)}
        />
        <fieldset className="challenge-picker">
          <legend>Choose your challenge</legend>
          <div className="tier-buttons">
            {challengeSizes.map((size) => (
              <button
                key={size}
                className={`tier-button${challengeSize === size ? ' is-active' : ''}`}
                type="button"
                aria-label={`${size} cards`}
                aria-pressed={challengeSize === size}
                onClick={() => setChallengeSize(size)}
              >
                <strong>{size}</strong>
                <span>cards</span>
              </button>
            ))}
          </div>
        </fieldset>
        <button
          className="button start-button"
          type="button"
          onClick={startGame}
        >
          Start timed challenge
        </button>
        <button
          className="text-button menu-help"
          type="button"
          onClick={() => setView('help')}
        >
          How to play
        </button>
      </section>
    </main>
  )
}
