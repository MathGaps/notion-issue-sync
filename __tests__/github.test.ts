import {getAttachedIssues} from '../src/core/github'
import {expect, test} from '@jest/globals'

test('throws invalid action', async () => {
  const input: any = {
    owner: 'MathGaps',
    name: 'notion-issue-sync',
    pr: 11
  }

  await expect(getAttachedIssues('invalid token', input)).rejects.toThrow()
})
