import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { canonicalDeck } from '../domain/deck'
import { SymbolCard } from './SymbolCard'

describe('SymbolCard', () => {
  it('renders eight selectable symbols and reports selections', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(
      <SymbolCard
        card={canonicalDeck[0]}
        label="Current card"
        seed={1}
        onSelect={onSelect}
      />,
    )

    expect(screen.getByLabelText('Current card')).toBeInTheDocument()
    const buttons = screen.getAllByRole('button', { name: /select/i })
    expect(buttons).toHaveLength(8)

    await user.click(buttons[0])
    expect(canonicalDeck[0].symbolIds).toContain(onSelect.mock.calls[0][0])
  })

  it('can disable selection during transitions', () => {
    render(
      <SymbolCard
        card={canonicalDeck[1]}
        label="Next card"
        seed={2}
        disabled
        onSelect={vi.fn()}
      />,
    )

    screen
      .getAllByRole('button', { name: /select/i })
      .forEach((button) => expect(button).toBeDisabled())
  })
})
