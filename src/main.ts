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
    const issues = await gh.getAttachedIssues()
    for (const {body} of issues) {
      if (body.includes('IDNo:')) {
        const prefix = `[${body.split('IDNo:')[1].trim()}] `
        await gh.addPrefixToPRTitle(prefix)
      }
    }
  } catch (error) {
    core.info(JSON.stringify(error))
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
