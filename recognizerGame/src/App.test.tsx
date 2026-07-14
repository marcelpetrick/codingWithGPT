import { fireEvent, render, screen } from '@testing-library/react'
import { act } from 'react'
import { App } from './App'

describe('App', () => {
  it('starts a selected challenge and shows the two game cards', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /20 cards/i }))
    fireEvent.click(
      screen.getByRole('button', { name: /start timed challenge/i }),
    )

    expect(screen.getByLabelText('Your current card')).toBeInTheDocument()
    expect(screen.getByLabelText('Next card')).toBeInTheDocument()
    expect(screen.getByText('0 of 19 matches')).toBeInTheDocument()
  })

  it('opens and closes the concise help screen', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /how to play/i }))

    expect(
      screen.getByRole('heading', { name: /find the one match/i }),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /back to menu/i }))

    expect(
      screen.getByRole('heading', { name: 'Recognizer' }),
    ).toBeInTheDocument()
  })

  it('can complete a short challenge by selecting the shared symbol', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-14T12:00:00Z'))
    render(<App />)
    fireEvent.click(
      screen.getByRole('button', { name: /start timed challenge/i }),
    )

    for (let decision = 0; decision < 9; decision += 1) {
      const currentButtons = Array.from(
        screen
          .getByLabelText('Your current card')
          .querySelectorAll<HTMLButtonElement>('button'),
      )
      const nextLabels = new Set(
        Array.from(
          screen
            .getByLabelText('Next card')
            .querySelectorAll<HTMLButtonElement>('button'),
        ).map((button) => button.getAttribute('aria-label')),
      )
      const matchingButton = currentButtons.find((button) =>
        nextLabels.has(button.getAttribute('aria-label')),
      )

      expect(matchingButton).toBeDefined()
      fireEvent.click(matchingButton!)
      act(() => vi.advanceTimersByTime(240))
    }

    expect(screen.getByText(/challenge complete/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Final time')).toBeInTheDocument()
    vi.useRealTimers()
  })
})
