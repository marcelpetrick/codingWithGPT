import {
  elapsedMilliseconds,
  finishTimer,
  formatDuration,
  startTimer,
} from './timer'

describe('wall-clock timer', () => {
  it('derives elapsed time from timestamps', () => {
    const timer = startTimer(1_000)
    expect(elapsedMilliseconds(timer, 64_456)).toBe(63_456)
  })

  it('freezes at the first finish timestamp', () => {
    const timer = finishTimer(startTimer(1_000), 3_456)
    expect(elapsedMilliseconds(timer, 99_999)).toBe(2_456)
    expect(finishTimer(timer, 8_000)).toEqual(timer)
  })

  it('formats active and result durations consistently', () => {
    expect(formatDuration(63_456)).toBe('01:03')
    expect(formatDuration(63_456, true)).toBe('01:03.45')
    expect(formatDuration(-1)).toBe('00:00')
  })
})
