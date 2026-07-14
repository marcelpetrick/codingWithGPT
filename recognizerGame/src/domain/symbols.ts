import birdImage from '../assets/symbols/bird.png'
import type { SymbolId } from './types'

export interface SymbolMetadata {
  readonly id: SymbolId
  readonly name: string
  readonly label: string
  readonly color: string
  readonly glyph: string
  readonly imageSrc?: string
}

const symbolDefinitions = [
  ['bird', 'Bird', '#3989db', '🐦', birdImage],
  ['tree', 'Tree', '#3f9a50', '🌳'],
  ['anchor', 'Anchor', '#8a6048', '⚓'],
  ['target', 'Target', '#d64740', '🎯'],
  ['cheese', 'Cheese', '#f5c94d', '🧀'],
  ['stone', 'Stone', '#78808a', '🪨'],
  ['ice-cube', 'Ice cube', '#75c9e8', '🧊'],
  ['igloo', 'Igloo', '#79bde8', '🛖'],
  ['carrot', 'Carrot', '#ef8a31', '🥕'],
  ['treble-clef', 'Treble clef', '#8b6049', '𝄞'],
  ['star', 'Star', '#f4bd2c', '⭐'],
  ['moon', 'Moon', '#7068b7', '🌙'],
  ['sun', 'Sun', '#f39f2d', '☀️'],
  ['crown', 'Crown', '#e6b63c', '👑'],
  ['key', 'Key', '#d8a637', '🔑'],
  ['apple', 'Apple', '#db4a45', '🍎'],
  ['mushroom', 'Mushroom', '#d95752', '🍄'],
  ['flower', 'Flower', '#dc5d98', '🌸'],
  ['fish', 'Fish', '#4098be', '🐟'],
  ['boat', 'Boat', '#658bd6', '⛵'],
  ['bell', 'Bell', '#e9b634', '🔔'],
  ['candle', 'Candle', '#e77a3d', '🕯️'],
  ['heart', 'Heart', '#d84652', '♥'],
  ['lightning-bolt', 'Lightning bolt', '#e7ba35', '⚡'],
  ['umbrella', 'Umbrella', '#527ad2', '☂'],
  ['house', 'House', '#db7951', '🏠'],
  ['mountain', 'Mountain', '#718ba5', '⛰️'],
  ['leaf', 'Leaf', '#62a64b', '🍃'],
  ['cup', 'Cup', '#bd6b48', '☕'],
  ['clock', 'Clock', '#7d8a9d', '🕐'],
  ['ladder', 'Ladder', '#b8743c', '🪜'],
  ['shell', 'Shell', '#db8b8a', '🐚'],
  ['balloon', 'Balloon', '#d55d77', '🎈'],
  ['cat', 'Cat', '#d58d49', '🐈'],
  ['dog', 'Dog', '#ae764d', '🐕'],
  ['turtle', 'Turtle', '#4e9c5d', '🐢'],
  ['butterfly', 'Butterfly', '#a56dc4', '🦋'],
  ['guitar', 'Guitar', '#ba7548', '🎸'],
  ['drum', 'Drum', '#ce5b4b', '🥁'],
  ['hammer', 'Hammer', '#77818b', '🔨'],
  ['magnet', 'Magnet', '#d24d4d', '🧲'],
  ['rocket', 'Rocket', '#7889d8', '🚀'],
  ['airplane', 'Airplane', '#6f9fbe', '✈️'],
  ['train', 'Train', '#d85b4a', '🚂'],
  ['bicycle', 'Bicycle', '#4f88b6', '🚲'],
  ['camera', 'Camera', '#57616c', '📷'],
  ['book', 'Book', '#5277c5', '📘'],
  ['pencil', 'Pencil', '#e3b13b', '✏️'],
  ['snowflake', 'Snowflake', '#70bde0', '❄'],
  ['castle', 'Castle', '#8b6ec2', '🏰'],
  ['boot', 'Boot', '#a3623e', '👢'],
  ['glasses', 'Glasses', '#565f6b', '👓'],
  ['diamond', 'Diamond', '#56b3d1', '♦'],
  ['cloud', 'Cloud', '#8fa5b7', '☁'],
  ['acorn', 'Acorn', '#9a6a42', '🌰'],
  ['ladybird', 'Ladybird', '#d84b4a', '🐞'],
  ['compass', 'Compass', '#c86b50', '🧭'],
] as const

export const symbolCatalog: readonly SymbolMetadata[] = symbolDefinitions.map(
  ([name, label, color, glyph, imageSrc], id) => ({
    id,
    name,
    label,
    color,
    glyph,
    ...(imageSrc ? { imageSrc } : {}),
  }),
)

export function getSymbolMetadata(symbolId: SymbolId): SymbolMetadata {
  const symbol = symbolCatalog[symbolId]
  if (!symbol) {
    throw new Error(`Unknown symbol ID: ${symbolId}`)
  }
  return symbol
}
