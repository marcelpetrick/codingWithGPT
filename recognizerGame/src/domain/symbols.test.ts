import { symbolCount } from './deck'
import { getSymbolMetadata, symbolCatalog } from './symbols'

describe('symbol catalog', () => {
  it('has one complete, unique entry for every deck symbol', () => {
    expect(symbolCatalog).toHaveLength(symbolCount)
    expect(new Set(symbolCatalog.map((symbol) => symbol.id)).size).toBe(
      symbolCount,
    )
    expect(new Set(symbolCatalog.map((symbol) => symbol.name)).size).toBe(
      symbolCount,
    )

    symbolCatalog.forEach((symbol, id) => {
      expect(symbol.id).toBe(id)
      expect(symbol.label).not.toHaveLength(0)
      expect(symbol.color).toMatch(/^#[0-9a-f]{6}$/i)
      expect(symbol.glyph).not.toHaveLength(0)
    })
  })

  it('returns metadata by stable ID', () => {
    expect(getSymbolMetadata(0).name).toBe('bird')
    expect(getSymbolMetadata(56).name).toBe('compass')
    expect(() => getSymbolMetadata(57)).toThrow('Unknown symbol ID')
  })
})
