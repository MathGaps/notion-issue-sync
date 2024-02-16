import * as github from '@actions/github'
import {GithubEvent} from '../types'

export default class Action {
  private octokit
  readonly event: GithubEvent

  constructor(token: string, jsonEvent: string) {
    this.octokit = github.getOctokit(token)
    this.event = JSON.parse(jsonEvent)
  }

  async run(): Promise<void> {
    if (this.event.label?.name === 'Released on @stable') {
      await this.markAsReleased()
    } else {
      await this.addPrefixToPRTitle()
    }
  }

  // Mark the issue/task as released by invoking the release webhook.
  private async markAsReleased(): Promise<void> {
    const res = await fetch(
      'https://hook.eu1.make.com/158u6i515f3xc12c2ah1uk0uyvirkdg4',
      {
        method: 'POST',
        body: JSON.stringify({
          id: this.event.pull_request.head.ref
        })
      }
    )
    if (!res.ok) {
      throw new Error(await res.text())
    }
  }

  // Lets Notion manage the state of the issue/task by adding the [NOTION-ID] prefix to the PR title.
  private async addPrefixToPRTitle(): Promise<void> {
    const title = this.event.pull_request.title
    const prefix = `[${this.event.pull_request.head.ref}]`
    if (
      !title.includes(prefix) &&
      !title.includes('ISSUE-') &&
      !title.includes('TASK-')
    ) {
      const newTitle = prefix + this.event.pull_request.title
      await this.octokit.rest.pulls.update({
        owner: github.context.repo.owner,
        repo: github.context.repo.repo,
        pull_number: this.event.pull_request.number,
        title: newTitle
      })
    }
  }
}
