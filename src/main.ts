import * as core from '@actions/core'
import Action from './core/github'

async function run(): Promise<void> {
  try {
    const token = core.getInput('token', {
      required: true
    })
    const event = core.getInput('event', {
      required: true
    })

    await new Action(token, event).run()
  } catch (error) {
    core.info(JSON.stringify(error))
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
