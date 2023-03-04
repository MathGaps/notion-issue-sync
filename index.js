const core = require("@actions/core");
const github = require("@actions/github");

// most @actions toolkit packages have async methods
async function run() {
  try {
    const webhook = core.getInput("webhook");
    const token = core.getInput("token");
    const octokit = github.getOctokit(token);
    const event = JSON.parse(core.getInput('event'));
    console.log(github.context.payload)
    const {
      repository: {
        closingIssuesReferences: { nodes: issues },
      },
    } = await octokit.graphql(
      `
    {
      repository(owner: $owner, name: $name) {
        closingIssuesReferences {
          nodes {
            body
          }
        }
      }
    }
`,
      {
        owner: github.context.repo.owner,
        name: github.context.repo.name,
      }
    );
    const ctx = {
      webhook,
      pr,
    }
    await updateStateForIssues(
      {
        webhook,

      },
      issues
    );
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
      }),
    });
  }
}

run();
