import { useEffect, useMemo, useRef, useState } from 'react'
import { SymbolCard } from './components/SymbolCard'
import { playFeedbackTone } from './feedback'
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
import { insertResult, isPersonalBest } from './domain/rankings'
import {
  clearGameData,
  defaultGameData,
  loadGameData,
  saveGameData,
  type StoredGameData,
} from './domain/storage'
import {
  challengeSizes,
  matchingDecisionCount,
  type SymbolId,
} from './domain/types'

type View = 'menu' | 'help' | 'game' | 'results' | 'rankings' | 'settings'

function displayName(name: string): string {
  return name.trim() || 'Player'
}

export function App() {
  const [view, setView] = useState<View>('menu')
  const [gameData, setGameData] = useState<StoredGameData>(() =>
    loadGameData(window.localStorage),
  )
  const [run, setRun] = useState<GameRun | null>(null)
  const [timer, setTimer] = useState<RunTimer | null>(null)
  const [now, setNow] = useState(0)
  const [selectedSymbolId, setSelectedSymbolId] = useState<SymbolId>()
  const [warning, setWarning] = useState('')
  const sessionId = useRef(0)
  const transitionTimeoutId = useRef<number | null>(null)
  const skipNextSave = useRef(false)
  const [resultSummary, setResultSummary] = useState<{
    rank?: number
    personalBest: boolean
    retained: boolean
  }>()

  const { playerName, challengeSize, soundEnabled, reducedMotion } =
    gameData.preferences

  const elapsed = timer ? elapsedMilliseconds(timer, now) : 0
  const decisionCount = matchingDecisionCount(challengeSize)

  useEffect(() => {
    if (skipNextSave.current) {
      skipNextSave.current = false
      return
    }
    saveGameData(window.localStorage, gameData)
  }, [gameData])

  useEffect(() => {
    document.documentElement.dataset.motion = reducedMotion ? 'reduced' : 'full'
  }, [reducedMotion])

  useEffect(() => {
    if (view !== 'game' || !timer || run?.phase === 'completed') {
      return undefined
    }

    const intervalId = window.setInterval(() => setNow(Date.now()), 100)
    return () => window.clearInterval(intervalId)
  }, [run?.phase, timer, view])

  useEffect(
    () => () => {
      if (transitionTimeoutId.current !== null) {
        window.clearTimeout(transitionTimeoutId.current)
      }
    },
    [],
  )

  const sharedSymbol = useMemo(
    () => (run && run.phase !== 'completed' ? currentMatch(run) : undefined),
    [run],
  )

  function startGame() {
    sessionId.current += 1
    if (transitionTimeoutId.current !== null) {
      window.clearTimeout(transitionTimeoutId.current)
      transitionTimeoutId.current = null
    }
    const newRun = createGameRun(
      createChallenge(challengeSize),
      Math.floor(Math.random() * 2_147_483_647),
    )
    const startedAt = Date.now()
    setRun(newRun)
    setTimer(startTimer(startedAt))
    setNow(startedAt)
    setSelectedSymbolId(undefined)
    setWarning('')
    setResultSummary(undefined)
    setView('game')
  }

  function updatePreferences(changes: Partial<StoredGameData['preferences']>) {
    setGameData((data) => ({
      ...data,
      preferences: { ...data.preferences, ...changes },
    }))
  }

  function handleSelection(symbolId: SymbolId) {
    if (!run || !timer) {
      return
    }

    const selection = selectSymbol(run, symbolId)
    setRun(selection.run)

    if (selection.result === 'incorrect') {
      if (soundEnabled) {
        playFeedbackTone('incorrect')
      }
      setWarning('Not the shared symbol — keep looking!')
      return
    }

    if (selection.result !== 'correct') {
      return
    }

    setWarning('')
    if (soundEnabled) {
      playFeedbackTone('correct')
    }
    setSelectedSymbolId(symbolId)
    const activeSessionId = sessionId.current
    transitionTimeoutId.current = window.setTimeout(() => {
      if (activeSessionId !== sessionId.current) {
        return
      }

      const nextRun = finishTransition(selection.run)
      setRun(nextRun)
      setSelectedSymbolId(undefined)

      if (nextRun.phase === 'completed') {
        const finishedTimer = finishTimer(timer, Date.now())
        const result = {
          id: `${finishedTimer.finishedAt ?? Date.now()}-${Math.random()}`,
          playerName: displayName(playerName),
          challengeSize,
          elapsedMs: elapsedMilliseconds(
            finishedTimer,
            finishedTimer.finishedAt ?? Date.now(),
          ),
          completedAt: finishedTimer.finishedAt ?? Date.now(),
        }
        const personalBest = isPersonalBest(gameData.rankings, result)
        const inserted = insertResult(
          gameData.rankings,
          result,
          gameData.nextInsertionOrder,
        )
        setGameData({
          ...gameData,
          rankings: inserted.rankings,
          nextInsertionOrder: gameData.nextInsertionOrder + 1,
        })
        setResultSummary({
          rank: inserted.rank,
          personalBest,
          retained: inserted.retained,
        })
        setTimer(finishedTimer)
        setNow(finishedTimer.finishedAt ?? Date.now())
        setView('results')
      }
      transitionTimeoutId.current = null
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
          {resultSummary?.personalBest && (
            <p className="achievement">New personal best!</p>
          )}
          {resultSummary?.retained && resultSummary.rank && (
            <p className="achievement">
              Rank #{resultSummary.rank} in this tier
            </p>
          )}
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
            <button
              className="text-button"
              type="button"
              onClick={() => setView('rankings')}
            >
              View rankings
            </button>
          </div>
        </section>
      </main>
    )
  }

  if (view === 'rankings') {
    const entries = gameData.rankings[challengeSize]
    return (
      <main className="app-shell">
        <section className="panel rankings-panel">
          <p className="eyebrow">Local rankings</p>
          <h1>{challengeSize}-card best times</h1>
          <ol className="ranking-list">
            {Array.from({ length: 10 }, (_, index) => {
              const entry = entries[index]
              return (
                <li key={entry?.id ?? `empty-${index}`}>
                  <span>{index + 1}</span>
                  <strong>{entry?.playerName ?? '—'}</strong>
                  <time>
                    {entry ? formatDuration(entry.elapsedMs, true) : '—'}
                  </time>
                </li>
              )
            })}
          </ol>
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

  if (view === 'settings') {
    return (
      <main className="app-shell">
        <section className="panel settings-panel">
          <p className="eyebrow">Settings</p>
          <h1>Play your way</h1>
          <label className="setting-toggle">
            <input
              type="checkbox"
              checked={soundEnabled}
              onChange={(event) =>
                updatePreferences({ soundEnabled: event.target.checked })
              }
            />
            Enable feedback sounds
          </label>
          <label className="setting-toggle">
            <input
              type="checkbox"
              checked={reducedMotion}
              onChange={(event) =>
                updatePreferences({ reducedMotion: event.target.checked })
              }
            />
            Reduce animations
          </label>
          <button
            className="button button-danger"
            type="button"
            onClick={() => {
              if (window.confirm('Clear all local rankings and preferences?')) {
                clearGameData(window.localStorage)
                skipNextSave.current = true
                setGameData(defaultGameData())
              }
            }}
          >
            Clear local game data
          </button>
          <button
            className="text-button menu-help"
            type="button"
            onClick={() => setView('menu')}
          >
            Back to menu
          </button>
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
                sessionId.current += 1
                if (transitionTimeoutId.current !== null) {
                  window.clearTimeout(transitionTimeoutId.current)
                  transitionTimeoutId.current = null
                }
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
            seed={run.layoutSeeds[run.cards[run.currentIndex].id]}
            selectedSymbolId={selectedSymbolId}
            disabled={run.phase !== 'active'}
            onSelect={handleSelection}
          />
          <SymbolCard
            card={run.cards[run.currentIndex + 1]}
            label="Next card"
            seed={run.layoutSeeds[run.cards[run.currentIndex + 1].id]}
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
          onChange={(event) =>
            updatePreferences({ playerName: event.target.value })
          }
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
                onClick={() => updatePreferences({ challengeSize: size })}
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
        <div className="menu-links">
          <button
            className="text-button"
            type="button"
            onClick={() => setView('rankings')}
          >
            Rankings
          </button>
          <button
            className="text-button"
            type="button"
            onClick={() => setView('settings')}
          >
            Settings
          </button>
        </div>
      </section>
    </main>
  )
}
