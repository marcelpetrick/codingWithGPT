import { render } from '@testing-library/react'
import { symbolCatalog } from '../domain/symbols'
import { SymbolMark } from './SymbolMark'
import { symbolIcons } from './symbolIcons'

describe('SymbolMark', () => {
  it('maps every catalog symbol to a consistent color-aware vector mark', () => {
    expect(Object.keys(symbolIcons)).toHaveLength(symbolCatalog.length)

    symbolCatalog.forEach((symbol) => {
      expect(symbolIcons[symbol.name]).toBeDefined()
      const { container, unmount } = render(<SymbolMark symbol={symbol} />)
      const icon = container.querySelector('svg')
      expect(icon).toHaveAttribute('fill', symbol.color)
      expect(icon).toHaveAttribute('stroke', '#172033')
      unmount()
    })
  })
})
