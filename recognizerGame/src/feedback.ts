export type FeedbackTone = 'correct' | 'incorrect'

/** Plays a brief optional tone without making game input depend on audio support. */
export function playFeedbackTone(tone: FeedbackTone): void {
  try {
    const context = new AudioContext()
    const oscillator = context.createOscillator()
    const gain = context.createGain()
    oscillator.type = tone === 'correct' ? 'triangle' : 'square'
    oscillator.frequency.value = tone === 'correct' ? 660 : 170
    gain.gain.setValueAtTime(0.035, context.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.12)
    oscillator.connect(gain)
    gain.connect(context.destination)
    oscillator.start()
    oscillator.stop(context.currentTime + 0.12)
    oscillator.addEventListener('ended', () => void context.close())
  } catch {
    // Audio is optional and can be unavailable until a browser gesture or on older devices.
  }
}
