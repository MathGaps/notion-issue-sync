const API = 'https://api.notion.com/v1'
const NOTION_VERSION = '2022-06-28'

// A Notion request that never throws: returns the parsed JSON, or an {object:'error'}
// dict on any HTTP/network failure. Callers treat errors as "skip/degrade" so a PR
// check can never turn red.
export async function notion(
  method: string,
  path: string,
  token: string,
  body?: unknown
): Promise<any> {
  try {
    const res = await fetch(API + path, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json'
      },
      body: body === undefined ? undefined : JSON.stringify(body)
    })
    return await res.json()
  } catch (e) {
    return {object: 'error', message: e instanceof Error ? e.message : String(e)}
  }
}
