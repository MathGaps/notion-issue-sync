const core = require("@actions/core"); const github = require("@actions/github");

// most @actions toolkit packages have async methods
async function run() {
  try {
    const webhook = core.getInput("webhook");
    const token = core.getInput("token");
    const octokit = github.getOctokit(token);
    const event = JSON.parse(core.getInput("event"));
    core.info(github.context.payload, event);
    const {
      repository: {
        pullRequest: {
          closingIssuesReferences: { nodes: issues },
        },
      },
    } = await octokit.graphql(
      `
    query($owner: String!, $name: String!, $pr: Int!) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $pr) {
          closingIssuesReferences(first: 10) {
            nodes {
              body
            }
          }
        }
      }
    }
`,
      {
        $owner: github.context.repo.owner,
        $name: github.context.repo.name,
        $pr: event.pull_request.number,
      }
    );
    const ctx = {
      webhook,
      pr,
    };
    await updateStateForIssues(ctx, issues);
  } catch (error) {
    core.setFailed(error.message);
  }
}

async function updateStateForIssues(webhook, issues) {
  for (const { body } of issues) {
    const [_, databaseID] = body.split("ID: ");
    fetch(webhook, {
      body: JSON.stringify({
        id: databaseID,
        // state: 'changes-requested' | 'in-pr' | 'in-qa' | 'in-review' | 'in-progress'
      }),
    });
  }
}

run();
