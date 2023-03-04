import * as github from '@actions/github'
import {GithubEvent, Issue, RepositoryResponse} from '../types'

export async function getAttachedIssues(
  token: string,
  ghEvent: GithubEvent
): Promise<Issue[]> {
  const octokit = github.getOctokit(token)

  const result: RepositoryResponse = await octokit.graphql(
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
      owner: ghEvent.owner,
      name: ghEvent.name,
      pr: ghEvent.pr
    }
  )

  return result.repository.pullRequest.closingIssuesReferences.nodes
}
