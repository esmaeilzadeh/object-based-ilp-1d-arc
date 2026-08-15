---
name: launch-remote-cursor-agent
description: >-
  Launch Cursor Cloud / remote agents with CURSOR_API_KEY from .env and the
  repo's pre-setup environment. Use when the user says remote agent, cloud
  agent, Cloud Agent VPS, run on Cursor Cloud, or asks to launch a bc- agent.
---

# Launch remote Cursor agent

## Auth

- Credential is **`CURSOR_API_KEY`**.
- Read it from the **repo-root `.env`** (`CURSOR_API_KEY=...`). Do not wait for
  it to already be exported. Typical load: `set -a; source .env; set +a`.
- Never print, log, or commit the value. `.env` is gitignored.

## Environment

If `.cursor/environment.json` exists, that **is** the proper pre-setup env.
Pass it on create:

```python
from cursor_sdk import Agent, CloudAgentOptions, CloudEnvironment, CloudRepository

cloud = CloudAgentOptions(
    env=CloudEnvironment(type="cloud", name=env_json["name"]),
    repos=[CloudRepository(url=repo_url, starting_ref=branch_or_sha)],
)
```

If the API rejects `env` + `repos` as mutually exclusive, keep the named `env`
(so the agent boots from the prepared Build) and still pin `starting_ref` if
the API allows it on the env object. Do not skip the named env and install from
scratch on a default VM.

This repo's known-good VPS: 4 vCPU → eval `JOBS=2`.

## Launch checklist

1. Load `CURSOR_API_KEY` from `.env`.
2. Push the branch/SHA to GitHub (cloud clones origin).
3. Create with named env + repo/ref; log `agent.agent_id` (`bc-…`) and run id.
4. Tell the remote agent to follow `.cursor/environment.json` `install` if cold.
5. Follow eval-hygiene (progress reports; no oversubscribe).
