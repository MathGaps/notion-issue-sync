import {expect, test} from '@jest/globals'
import Github from '../src/core/github'

test('Github class test', function () {
  expect(() => {
    new Github('invalid token', '{"wrong": "input"}')
  }).toThrowError()
})
