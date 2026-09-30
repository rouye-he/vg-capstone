# OpenClaw + iMessage runbook (Richard's Mac, 2026-09-30)

Second real-device environment for Phase 1, set up alongside Rouye's Mac. Everything below was run on this machine; items marked **manual** need a person at the keyboard (System Settings dialogs, Apple ID password, API key).

## Machine

| Item | Value |
| --- | --- |
| macOS | 15.7.3 Sequoia (meets the imsg requirement of 14+) |
| Node | 26.10.0 (Homebrew) |
| imsg | 0.15.9 (`brew install steipete/tap/imsg`) |
| OpenClaw | 2026.9.7 (`npm install -g openclaw`) |
| iMessage plugin | `@openclaw/imessage`, installed to `~/.openclaw/npm/projects/openclaw-imessage-*` |
| Config | `~/.openclaw/openclaw.json` (validated with `openclaw config validate`) |

## Done

```bash
brew install node
brew install steipete/tap/imsg
npm install -g openclaw
openclaw plugins install @openclaw/imessage
openclaw config set gateway.mode local
openclaw doctor --fix --generate-gateway-token
openclaw config set channels.imessage.enabled true
openclaw config set channels.imessage.cliPath '"/opt/homebrew/bin/imsg"'
openclaw config set channels.imessage.dbPath '"/Users/richardzhu/Library/Messages/chat.db"'
openclaw config set channels.imessage.dmPolicy '"pairing"'        # nobody talks to the bot until approved
openclaw config set channels.imessage.groupPolicy '"disabled"'    # MVP: DMs only
openclaw config set channels.imessage.includeAttachments true     # off by default; attachment-only messages would be dropped
openclaw config set channels.imessage.mediaMaxMb 16
openclaw config set channels.imessage.textChunkLimit 4000
openclaw config set channels.imessage.configWrites false          # chat cannot rewrite config
openclaw config set agents.defaults.model '"anthropic/claude-opus-5-5"'
```

Resulting `channels.imessage` block:

```json
{
  "enabled": true,
  "cliPath": "/opt/homebrew/bin/imsg",
  "dbPath": "/Users/richardzhu/Library/Messages/chat.db",
  "dmPolicy": "pairing",
  "groupPolicy": "disabled",
  "includeAttachments": true,
  "mediaMaxMb": 16,
  "textChunkLimit": 4000,
  "configWrites": false
}
```

## Gateway smoke test (40 s run, 2026-09-30 17:15)

The gateway starts cleanly and fails at exactly the expected point:

```text
[gateway]  agent model: anthropic/claude-opus-5-5 (thinking=medium, fast=off)
[gateway]  http server listening (15 plugins: ... imessage ...)
[imessage] [default] starting provider (/opt/homebrew/bin/imsg db=/Users/richardzhu/Library/Messages/chat.db)
[gateway]  ready
[imessage] imsg rpc not ready after 10613ms (IMessageRpcRequestError: Database unavailable: code=-32002
           "The configured Messages database could not be opened read-only. Verify the path and grant
            Full Disk Access to the supervising process, then retry."
[imessage] [default] auto-restart attempt 1/10 in 5s
```

So plugin loading, config, `imsg rpc` spawning and the channel supervisor all work. Step 1 below is the only thing between this and a live channel (plus a model key for replies).

## Remaining, in order

1. **manual** Grant Full Disk Access: System Settings > Privacy & Security > Full Disk Access, add Terminal (and iTerm / VS Code if you launch from there). Restart the terminal. Verify:
   ```bash
   imsg chats --limit 5 --json
   ```
   Today this returns `authorization denied (code: 23)`, which is exactly the Full Disk Access error.
2. **manual** Grant Automation for Messages: the first `imsg send` triggers the prompt.
   ```bash
   imsg send --to <your own number> --text "imsg test"
   ```
3. **manual** Provide a model credential. No Anthropic key is present on this machine (checked env, shell rc files, `ant` CLI not installed). Either:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...   # in ~/.zshrc, then restart the terminal
   ```
   or run `openclaw configure` and pick Anthropic. Check with `openclaw models list --refresh`.
4. Start the gateway and confirm the channel is up:
   ```bash
   openclaw gateway            # foreground, watch the log
   openclaw channels status --probe
   ```
5. Send a DM to this Mac's iMessage from your phone. The gateway logs a pairing code. Approve it:
   ```bash
   openclaw pairing list imessage
   openclaw pairing approve imessage <CODE>
   ```
   Pairing requests expire after 1 hour. The first approval also records the command owner.
6. Send a second message and confirm a reply arrives. Then try a PDF and a HEIC photo.
7. Record the raw traffic for the Simulator:
   ```bash
   imsg history --chat-id <id> --limit 20 --attachments --json > imessage-simulator/fixtures/imsg_real_capture.ndjson
   cd imessage-simulator && python -m imsg_sim.raw_events fixtures/imsg_real_capture.ndjson
   ```
   Strip anything personal before committing.
8. Optional but recommended before the demo: run under a dedicated macOS user (`vgbot`) with the dedicated Apple ID, so the gateway never reads a personal `chat.db`. Steps are in the design PDF, Deployment log. Creating the user needs an admin password (`sysadminctl -addUser vgbot ...` or System Settings > Users & Groups).

## Findings worth telling the sponsor

- The OpenClaw iMessage channel installs and configures without touching Messages. The only blocking dependencies are macOS permissions and a signed-in Apple ID.
- `includeAttachments` defaults to off. Without it the invoice-PDF use case silently drops.
- `dmPolicy: pairing` is OpenClaw's first identity gate. It decides who may talk to the bot, not what role they have. VG's principal / delegate / colleague / external roles still need VG's IAM layer in front of or inside the agent.
- Group chats are disabled at the channel level for the MVP. Re-enabling them later means setting `groupPolicy: allowlist`, `groupAllowFrom`, and a `groups` map, and mention gating is derived from the agent's identity name.
- Inbound recovery after a restart is built into the plugin (durable ingress journal keyed by Apple GUID, `since_rowid` replay, stale backlog fence). Option C from the design doc would have to rebuild all of this.
- Split-send (command then URL) is coalesced by imsg 0.13.1+ before OpenClaw sees it. No channel-side setting.
