import { fireEvent, render, screen } from '@testing-library/react'
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
})
