// Pure event -> status mapping. No I/O, fully unit-tested.
export type PrRowKey = 'draft' | 'open' | 'merged' | 'closed'
export type IssueKey = 'in_pr' | 'fixes_required' | 'for_qa'

// The PR's own row in the Pull Requests DB: Draft / Open / Merged / Closed.
export function prRowStatusKey(event: any): PrRowKey | null {
  if (event.review) return null // reviews don't change the PR row
  const pr = event.pull_request ?? {}
  const action = event.action
  if (action === 'closed') return pr.merged ? 'merged' : 'closed'
  if (action === 'converted_to_draft') return 'draft'
  if (action === 'opened' || action === 'reopened') return pr.draft ? 'draft' : 'open'
  if (action === 'ready_for_review') return 'open'
  return null
}

// The linked issue's Status: In PR / Fixes Required / For QA (For QA is gated on siblings).
export function issueStatusKey(event: any): IssueKey | null {
  const review = event.review
  const pr = event.pull_request ?? {}
  const action = event.action
  if (review) {
    return action === 'submitted' && review.state === 'changes_requested'
      ? 'fixes_required'
      : null
  }
  if (
    (action === 'opened' || action === 'ready_for_review' || action === 'reopened') &&
    !pr.draft
  )
    return 'in_pr'
  if (action === 'closed' && pr.merged) return 'for_qa'
  return null
}

// Extract the issue number from an [ISSUE-N] / TASK-N reference (fallback resolution).
export function parseUniqueId(text: string | undefined | null): number | null {
  if (!text) return null
  const m = /\b(?:ISSUE|TASK)-(\d+)\b/i.exec(text)
  return m ? parseInt(m[1], 10) : null
}
