// Workspace config. Property names match the Notion databases; update here if they change.
export const config = {
  // Issues database (Tech Issues) — used only by the [ISSUE-N] body fallback.
  issuesDb: '0cabad23-7e62-4481-bd8c-48c8a4a08a7b',
  idProp: 'ID', // unique_id property (prefix ISSUE)

  // Pull Requests database — one row per PR, related to its issue(s).
  prsDb: '390bfd2f-80ba-80f3-88b0-ce0b805397da',
  prUrlProp: 'URL',
  prStatusProp: 'Status',

  // One entry per PRs-DB relation column. The column identifies the linked issue's
  // database, and carries that database's Status vocabulary. A Tech Issue only ever
  // appears in the Tech column and a task only in the Task column.
  relations: [
    {
      column: '🐛 Tech Issues',
      statusProp: 'Status',
      status: {in_pr: 'In PR', fixes_required: 'Fixes Required', for_qa: 'For QA'}
    },
    {
      column: '✅ Task List',
      statusProp: 'Status',
      status: {in_pr: 'In PR', fixes_required: 'Fixes Required', for_qa: 'Ready For Review'}
    }
  ],

  prStatus: {
    draft: 'Draft',
    open: 'Open',
    merged: 'Merged',
    closed: 'Closed'
  }
} as const
