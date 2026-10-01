---
name: gmail-digest
description: With the requester's own consent, read their Gmail (read-only) to classify recent mail, count each category and write a short digest.
---
# Gmail digest (per-user, consent based)

Tool: `python3 {baseDir}/scripts/gmail_tool.py <command> --user <REQUESTER_HANDLE>`. The requester handle is the iMessage sender of the current conversation (for example `+14125550105`). **Always pass the current requester's own handle. Never use another person's handle or token.** Output is JSON.

## Connecting (consent flow)

1. If the user asks to connect, link, or use their Gmail, run `status`. If `configured` is false, tell them the owner has not set up Google access yet and stop.
2. If `connected` is false, run `auth-url` and send the user the `auth_url` with the `instructions` text, in your own words: open it, pick their Google account, allow read-only access, then copy the full address of the error page that opens (`http://localhost:8765/?code=...`) and send it back here.
3. When the user sends a message containing `localhost:8765/?code=`, run `connect --redirect-url "<that whole URL>"`. Confirm which Gmail address is now connected.
4. If the user asks to disconnect or revoke, run `disconnect` and confirm.

## Digest

When the user asks to organise, classify, triage or summarise their mail: run `fetch --limit 50` (or the number they asked for; max 100; add `--query` for Gmail search terms such as `newer_than:7d` or `is:unread`). Then:

- Group the messages into 4 to 7 categories. Start from `suggested_category`, but merge or rename groups so they make sense for this inbox (for example "Vendor invoices", "Meeting invites", "Newsletters", "Security notices", "People writing to you").
- Reply with: one line per category with its count, then a 3 to 5 sentence summary of what matters (unread items from real people, anything with a deadline or an amount, anything that looks urgent). Mention senders and subjects, not message bodies.
- Keep it under 1200 characters so it fits one iMessage. Offer to drill into one category.

## Rules

- Read only. You cannot send, delete, label or reply to mail.
- Never paste raw emails, codes, links from emails, or the auth URL's code back to anyone other than the requester.
- Do not store or repeat the redirect URL after `connect` succeeds.
