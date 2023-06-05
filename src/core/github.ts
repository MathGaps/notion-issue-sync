import * as github from '@actions/github'
import {GithubEvent} from '../types'

export default class Github {
  private octokit
  private ghEvent: GithubEvent
  constructor(token: string, jsonEvent: string) {
    this.octokit = github.getOctokit(token)
    const event = JSON.parse(jsonEvent)
    this.ghEvent = {
      owner: github.context.repo.owner,
      repoName: github.context.repo.repo,
      pr: event.pull_request.number,
      title: event.pull_request.title,
      branch: event.pull_request.head.ref
    }
  }
  get githubEvent(): GithubEvent {
    return this.ghEvent
  }
  async addPrefixToPRTitle(prefix: string): Promise<void> {
    if (!this.ghEvent.title.includes(prefix)) {
      const newTitle = prefix + this.ghEvent.title
      await this.octokit.rest.pulls.update({
        owner: this.ghEvent.owner,
        pull_number: this.ghEvent.pr,
        repo: this.ghEvent.repoName,
        title: newTitle
      })
    }
  }
}
