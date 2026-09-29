# Managed settings change requests

Claude Code runs with company-wide managed settings (see [Current managed settings](Current-Managed-Settings)).
If they block something you need for your work, request a change.

## How

1. Open a ticket in this project.
2. Assign it to **Alex Berger** or **Marcel Petrick**.
3. Fill in the template below.

## Ticket template

```markdown
### What is not working
<!-- The command or action, and the exact error message. -->

### What I would like
<!-- The behaviour you need. -->

### How
<!-- Your proposed change, ideally as a settings snippet, e.g.
"sandbox": { "excludedCommands": ["nvidia-smi"] } -->

### Why
<!-- Your use case, and why a local setting or a workaround is not enough. -->
```

## Decision

Alex Berger and Marcel Petrick discuss each request and record the decision in the ticket.
If a request is accepted, the change is deployed and [Current managed settings](Current-Managed-Settings) is updated.
