import * as core from '@actions/core'
import * as github from '@actions/github'
import {run} from './run'

// Non-fatal by design: warnings only, never setFailed, so a Notion hiccup or a
// missing token can't turn a PR check red.
async function main(): Promise<void> {
  try {
    const token = core.getInput('notion_token')
    if (!token) {
      core.warning('notion_token not set; skipping (non-fatal).')
      return
    }
    await run(github.context.payload, token)
  } catch (error) {
    core.warning(`notion-status: ${error instanceof Error ? error.message : String(error)}`)
  }
}

main()
