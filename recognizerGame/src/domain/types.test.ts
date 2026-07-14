import { challengeSizes, isChallengeSize, matchingDecisionCount } from './types'

describe('challenge sizes', () => {
  it('only allows the agreed total-card tiers', () => {
    expect(challengeSizes).toEqual([10, 20, 50])
    expect(isChallengeSize(10)).toBe(true)
    expect(isChallengeSize(20)).toBe(true)
    expect(isChallengeSize(50)).toBe(true)
    expect(isChallengeSize(9)).toBe(false)
    expect(isChallengeSize(57)).toBe(false)
  })

  it('derives matching decisions from total cards', () => {
    expect(matchingDecisionCount(10)).toBe(9)
    expect(matchingDecisionCount(20)).toBe(19)
    expect(matchingDecisionCount(50)).toBe(49)
  })
})
