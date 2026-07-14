import { render, screen } from '@testing-library/react'
import { App } from './App'

describe('App', () => {
  it('renders the game introduction', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'Recognizer' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/one symbol shared/i)).toBeInTheDocument()
  })
})
