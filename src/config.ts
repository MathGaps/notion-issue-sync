// Workspace config. Property names match the Notion databases; update here if they change.
export const config = {
  // Tech Issues (the issues database)
  issuesDb: '0cabad23-7e62-4481-bd8c-48c8a4a08a7b',
  idProp: 'ID', // unique_id property (prefix ISSUE)
  issueStatusProp: 'Status',

  // Pull Requests database (one row per PR, related to its issue)
  prsDb: '390bfd2f-80ba-80f3-88b0-ce0b805397da',
  prUrlProp: 'URL',
  prIssueRelation: '🐛 Tech Issues',
  prStatusProp: 'Status',

  issueStatus: {
    in_pr: 'In PR',
    fixes_required: 'Fixes Required',
    for_qa: 'For QA'
  },
  prStatus: {
    draft: 'Draft',
    open: 'Open',
    merged: 'Merged',
    closed: 'Closed'
  }
} as const
