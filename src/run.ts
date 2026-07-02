import * as core from '@actions/core'
import {config} from './config'
import {notion} from './notion'
import {issueStatusKey, parseUniqueId, prRowStatusKey} from './transitions'

async function findPrRow(prUrl: string | undefined, token: string): Promise<any> {
  if (!prUrl) return null
  const res = await notion('POST', `/databases/${config.prsDb}/query`, token, {
    filter: {property: config.prUrlProp, url: {equals: prUrl}},
    page_size: 1
  })
  if (res.object === 'error') {
    core.warning(`Pull Requests DB unavailable (${res.code ?? res.message}).`)
    return null
  }
  return res.results?.[0] ?? null
}

function issueIdFromRow(row: any): string | null {
  const rel = row?.properties?.[config.prIssueRelation]?.relation ?? []
  return rel[0]?.id ?? null
}

async function resolveIssueViaBody(
  body: string | undefined,
  token: string
): Promise<string | null> {
  const number = parseUniqueId(body)
  if (number == null) return null
  const res = await notion('POST', `/databases/${config.issuesDb}/query`, token, {
    filter: {property: config.idProp, unique_id: {equals: number}},
    page_size: 1
  })
  if (res.object === 'error') return null
  return res.results?.[0]?.id ?? null
}

async function setStatus(
  pageId: string,
  prop: string,
  name: string,
  token: string
): Promise<boolean> {
  const res = await notion('PATCH', `/pages/${pageId}`, token, {
    properties: {[prop]: {status: {name}}}
  })
  if (res.object === 'error') {
    core.warning(`Failed to set ${prop} -> ${name}: ${res.message}`)
    return false
  }
  return true
}

// True if every linked PR row OTHER than the current one is Merged/Closed.
// Returns null if the rows can't be read (caller decides).
async function othersAllDone(
  issueId: string,
  currentRowId: string | null,
  token: string
): Promise<boolean | null> {
  const done = new Set<string>([config.prStatus.merged, config.prStatus.closed])
  const res = await notion('POST', `/databases/${config.prsDb}/query`, token, {
    filter: {property: config.prIssueRelation, relation: {contains: issueId}}
  })
  if (res.object === 'error') return null
  const open: unknown[] = []
  for (const row of res.results ?? []) {
    if (row.id === currentRowId) continue
    const status = row.properties?.[config.prStatusProp]?.status?.name
    if (!done.has(status)) open.push([row.properties?.[config.prUrlProp]?.url, status])
  }
  if (open.length) {
    core.info(`sibling PR(s) not done: ${JSON.stringify(open)}`)
    return false
  }
  return true
}

export async function run(event: any, token: string): Promise<void> {
  const pr = event.pull_request ?? {}
  const prUrl: string | undefined = pr.html_url
  const row = await findPrRow(prUrl, token)
  const issueId = row ? issueIdFromRow(row) : await resolveIssueViaBody(pr.body, token)

  // 1) PR row Status (Draft / Open / Merged / Closed)
  const rowKey = prRowStatusKey(event)
  if (rowKey) {
    if (row) {
      const name = config.prStatus[rowKey]
      core.info(`set PR row -> ${name}`)
      await setStatus(row.id, config.prStatusProp, name, token)
    } else {
      core.info(`no PR row for ${prUrl} (link it first); skipping PR-row status.`)
    }
  }

  // 2) Issue Status (In PR / Fixes Required / For QA)
  const issueKey = issueStatusKey(event)
  if (!issueKey) {
    core.info('No issue-status transition for this event.')
    return
  }
  if (!issueId) {
    core.info(`Could not resolve a Notion issue for ${prUrl}; skipping issue status.`)
    return
  }
  if (issueKey === 'for_qa') {
    const done = await othersAllDone(issueId, row?.id ?? null, token)
    if (done === false) {
      core.info('Merged, but sibling PRs are still open; leaving issue status unchanged.')
      return
    }
    if (done === null) {
      core.warning('Could not read sibling rows; leaving issue status unchanged (fail-safe).')
      return
    }
  }
  const name = config.issueStatus[issueKey]
  core.info(`set issue -> ${name}`)
  await setStatus(issueId, config.issueStatusProp, name, token)
}
