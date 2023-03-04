import {sendWebhookStateUpdate} from '../src/core/webhook_state'
import {expect, test} from '@jest/globals'

test('throws invalid action', async () => {
  const input: any = {
    event: {
      action: 'invalid_action'
    },
    issues: [
      {
        body: 'ID: example id'
      }
    ]
  }

  await expect(sendWebhookStateUpdate(input)).rejects.toThrow(
    `invalid action ${input.event.action}`
  )
})
