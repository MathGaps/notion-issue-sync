import * as core from '@actions/core'
import * as github from '@actions/github'
import {GithubEvent} from './types'

import {sendWebhookStateUpdate} from './core/webhook_state'
import {getAttachedIssues} from './core/github'

async function run(): Promise<void> {
  try {
    const webhook = core.getInput('webhook', {
      required: true
    })
    const token = core.getInput('token', {
      required: true
    })
    const event = JSON.parse(
      core.getInput('event', {
        required: true
      })
    )

    const ghEvent: GithubEvent = {
      action: event.action,
      owner: github.context.repo.owner,
      name: github.context.repo.repo,
      pr: event.pull_request.number,
      merged: event.pull_request.merged,
      body: event.pull_request.body,
      reviewState: event.review?.state
    }

    await sendWebhookStateUpdate({
      issues: await getAttachedIssues(token, ghEvent),
      event: ghEvent,
      webhook
    })
  } catch (error) {
    core.info(JSON.stringify(error))
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
