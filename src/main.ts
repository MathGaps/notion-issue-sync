import * as core from '@actions/core'
import Github from './core/github'

async function run(): Promise<void> {
  try {
    const token = core.getInput('token', {
      required: true
    })
    const event = core.getInput('event', {
      required: true
    })

    const gh = new Github(token, event)
    const prefix = `[${gh.githubEvent.branch}]`
    await gh.addPrefixToPRTitle(prefix)
  } catch (error) {
    core.info(JSON.stringify(error))
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
