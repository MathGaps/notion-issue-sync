import {expect, test} from '@jest/globals'
import {resolveIssues} from '../src/run'

test('resolveIssues collects every issue across both relations, with per-DB status', () => {
  const row = {
    properties: {
      '🐛 Tech Issues': {relation: [{id: 'tech-1'}, {id: 'tech-2'}]},
      '✅ Task List': {relation: [{id: 'task-1'}]}
    }
  }
  const got = resolveIssues(row)
  expect(got.map(i => i.pageId)).toEqual(['tech-1', 'tech-2', 'task-1'])
  expect(got[0].relation.column).toBe('🐛 Tech Issues')
  expect(got[0].relation.status.for_qa).toBe('For QA')
  expect(got[2].relation.column).toBe('✅ Task List')
  expect(got[2].relation.status.for_qa).toBe('Ready For Review')
})

test('resolveIssues handles empty / missing relations', () => {
  expect(resolveIssues({properties: {}})).toEqual([])
  expect(resolveIssues(null)).toEqual([])
})
