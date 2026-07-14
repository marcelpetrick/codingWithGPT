export interface RunTimer {
  readonly startedAt: number
  readonly finishedAt?: number
}

export function startTimer(now: number): RunTimer {
  return { startedAt: now }
}

export function finishTimer(timer: RunTimer, now: number): RunTimer {
  return timer.finishedAt === undefined ? { ...timer, finishedAt: now } : timer
}

export function elapsedMilliseconds(timer: RunTimer, now: number): number {
  return Math.max(0, (timer.finishedAt ?? now) - timer.startedAt)
}

export function formatDuration(
  milliseconds: number,
  includeHundredths = false,
): string {
  const safeMilliseconds = Math.max(0, Math.floor(milliseconds))
  const minutes = Math.floor(safeMilliseconds / 60_000)
  const seconds = Math.floor((safeMilliseconds % 60_000) / 1_000)
  const prefix = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`

  if (!includeHundredths) {
    return prefix
  }

  return `${prefix}.${String(Math.floor((safeMilliseconds % 1_000) / 10)).padStart(2, '0')}`
}
