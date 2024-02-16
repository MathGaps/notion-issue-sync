export type GithubEvent = {
  label:
    | {
        name: string
      }
    | undefined
  pull_request: {
    number: number
    title: string
    head: {
      // Branch
      ref: string
    }
  }
}
