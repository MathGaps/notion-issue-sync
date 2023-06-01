import * as github from '@actions/github'
import { GithubEvent, Issue, RepositoryResponse } from '../types'

export default class Github {
  private octokit
  private ghEvent: GithubEvent
  constructor(token: string, jsonEvent: string) {
    this.octokit = github.getOctokit(token)
    const event = JSON.parse(jsonEvent)
    this.ghEvent = {
      action: event.action,
      owner: github.context.repo.owner,
      repoName: github.context.repo.repo,
      pr: event.pull_request.number,
      title: event.pull_request.title,
      merged: event.pull_request.merged,
      body: event.pull_request.body,
      reviewState: event.review?.state
    }
  }

  async getAttachedIssues(): Promise<Issue[]> {
    const result: RepositoryResponse = await this.octokit.graphql(
      `
        query($owner: String!, $name: String!, $pr: Int!) {
        repository(owner: $owner, name: $name) {
          pullRequest(number: $pr) {
            closingIssuesReferences(first: 10) {
              nodes {
                body
              }
            }
          }
        }
      }
      `,
      {
        owner: this.ghEvent.owner,
        name: this.ghEvent.repoName,
        pr: this.ghEvent.pr
      }
    )

    return result.repository.pullRequest.closingIssuesReferences.nodes
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
