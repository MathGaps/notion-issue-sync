import axios from 'axios'
import {GithubEvent, NotionState, UpdateStatePayload} from '../types'

function mapPRStateToNotionState(event: GithubEvent): NotionState {
  switch (event.action) {
    case 'opened':
    case 'reopened':
      return 'In progress'

    case 'closed': {
      if (event.merged) return 'For QA'
      else return 'Archived'
    }

    case 'submitted': {
      if (event.reviewState !== 'approved') return 'Fixes Required'
      else return 'In progress'
    }
    case 'created': {
      return 'Fixes Required'
    }

    default:
      throw new Error(`invalid action ${event.action}`)
  }
}

export async function sendWebhookStateUpdate(
  payload: UpdateStatePayload
): Promise<void> {
  for (const {body} of payload.issues) {
    if (body.includes('ID:')) {
      const ID = body.split('ID: ')[1].trim()
      await axios.post(payload.webhook, {
        id: ID,
        state: mapPRStateToNotionState(payload.event)
      })
    }
  }
}
