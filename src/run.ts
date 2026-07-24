import * as core from '@actions/core'
import {config} from './config'
import {notion} from './notion'
import {issueStatusKey, parseUniqueId, prRowStatusKey} from './transitions'

type RelationConfig = (typeof config.relations)[number]
type LinkedIssue = {pageId: string; relation: RelationConfig}

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

// Every issue linked to a PR row, across all relation columns (a PR can fix many issues).
export function resolveIssues(row: any): LinkedIssue[] {
  const issues: LinkedIssue[] = []
  for (const relation of config.relations) {
    const rel = row?.properties?.[relation.column]?.relation ?? []
    for (const r of rel) {
      if (r?.id) issues.push({pageId: r.id, relation})
    }
  }
  return issues
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

// True if every PR row OTHER than the current one linked to this issue (via the given
// relation column) is Merged/Closed. Returns null if the rows can't be read.
async function othersAllDone(
  issueId: string,
  currentRowId: string | null,
  relationColumn: string,
  token: string
): Promise<boolean | null> {
  const done = new Set<string>([config.prStatus.merged, config.prStatus.closed])
  const res = await notion('POST', `/databases/${config.prsDb}/query`, token, {
    filter: {property: relationColumn, relation: {contains: issueId}}
  })
  if (res.object === 'error') return null
  const open: unknown[] = []
  for (const row of res.results ?? []) {
    if (row.id === currentRowId) continue
    const status = row.properties?.[config.prStatusProp]?.status?.name
    if (!done.has(status)) open.push([row.properties?.[config.prUrlProp]?.url, status])
  }
  if (open.length) {
    core.info(`issue ${issueId}: sibling PR(s) not done: ${JSON.stringify(open)}`)
    return false
  }
  return true
}

export async function run(event: any, token: string): Promise<void> {
  const pr = event.pull_request ?? {}
  const prUrl: string | undefined = pr.html_url
  const row = await findPrRow(prUrl, token)

  // Every issue this PR is linked to (a PR can fix several, across both databases).
  let issues: LinkedIssue[]
  if (row) {
    issues = resolveIssues(row)
  } else {
    const fallbackId = await resolveIssueViaBody(pr.body, token)
    issues = fallbackId ? [{pageId: fallbackId, relation: config.relations[0]}] : []
  }

  // 1) PR row Status (Draft / Open / Merged / Closed) — one row.
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

  // 2) Issue Status (In PR / Fixes Required / For QA) — for EVERY linked issue.
  const issueKey = issueStatusKey(event)
  if (!issueKey) {
    core.info('No issue-status transition for this event.')
    return
  }
  if (issues.length === 0) {
    core.info(`Could not resolve any Notion issue for ${prUrl}; skipping issue status.`)
    return
  }

  for (const {pageId, relation} of issues) {
    // "For QA" only when all of THIS issue's own PRs are merged/closed.
    if (issueKey === 'for_qa') {
      const done = await othersAllDone(pageId, row?.id ?? null, relation.column, token)
      if (done === false) {
        core.info(`issue ${pageId}: sibling PRs still open; leaving unchanged.`)
        continue
      }
      if (done === null) {
        core.warning(`issue ${pageId}: could not read sibling rows; leaving unchanged (fail-safe).`)
        continue
      }
    }
    const name = relation.status[issueKey]
    core.info(`set issue ${pageId} -> ${name} (via ${relation.column})`)
    await setStatus(pageId, relation.statusProp, name, token)
  }
}
