import {expect, test} from '@jest/globals'
import {issueStatusKey, parseUniqueId, prRowStatusKey} from '../src/transitions'

const ev = (action: string, pr: any = {}): any => ({action, pull_request: pr})
const review = (state: string): any => ({action: 'submitted', review: {state}, pull_request: {}})

test('prRowStatusKey maps PR events to the row status', () => {
  expect(prRowStatusKey(ev('opened', {draft: false}))).toBe('open')
  expect(prRowStatusKey(ev('opened', {draft: true}))).toBe('draft')
  expect(prRowStatusKey(ev('converted_to_draft'))).toBe('draft')
  expect(prRowStatusKey(ev('ready_for_review', {draft: false}))).toBe('open')
  expect(prRowStatusKey(ev('reopened', {draft: false}))).toBe('open')
  expect(prRowStatusKey(ev('closed', {merged: true}))).toBe('merged')
  expect(prRowStatusKey(ev('closed', {merged: false}))).toBe('closed')
  expect(prRowStatusKey(review('changes_requested'))).toBeNull()
})

test('issueStatusKey maps PR events to the issue status', () => {
  expect(issueStatusKey(ev('opened', {draft: false}))).toBe('in_pr')
  expect(issueStatusKey(ev('opened', {draft: true}))).toBeNull()
  expect(issueStatusKey(ev('ready_for_review', {draft: false}))).toBe('in_pr')
  expect(issueStatusKey(ev('reopened', {draft: false}))).toBe('in_pr')
  expect(issueStatusKey(ev('reopened', {draft: true}))).toBeNull()
  expect(issueStatusKey(ev('closed', {merged: true}))).toBe('for_qa')
  expect(issueStatusKey(ev('closed', {merged: false}))).toBeNull()
  expect(issueStatusKey(review('changes_requested'))).toBe('fixes_required')
  expect(issueStatusKey(review('approved'))).toBeNull()
  expect(issueStatusKey(review('commented'))).toBeNull()
})

test('parseUniqueId extracts the issue number', () => {
  expect(parseUniqueId('body\nNotion: ISSUE-21360')).toBe(21360)
  expect(parseUniqueId('see TASK-42 here')).toBe(42)
  expect(parseUniqueId('nothing here')).toBeNull()
  expect(parseUniqueId(undefined)).toBeNull()
})
