# MANDATORY CLAUDE PROTOCOL - READ FIRST

**This document contains MANDATORY instructions for Claude. Failure to follow these will waste the user's time.**

---

## RULE 1: RUN SSH COMMANDS DIRECTLY - NEVER ASK USER TO COPY/PASTE

**ALWAYS** use the Bash tool to run SSH commands directly:

```bash
ssh root@167.172.54.56 "command here"
```

**NEVER** output an SSH command and ask the user to copy/paste it.

This works. It has been tested. There is NO excuse for asking the user to manually run commands.

### Examples of what TO DO:
```
<use Bash tool>
ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"
</use Bash tool>
```

### Examples of what NOT TO DO:
```
Run this command:
ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"
```

The user spent an ENTIRE DAY copying and pasting commands on 14 January 2026 because Claude failed to run them directly. This was completely unnecessary and wasted hours of the user's time.

---

## RULE 2: RECOVERY FIRST, QUESTIONS LATER

If the user reports 502 Bad Gateway or any service outage:

1. **IMMEDIATELY** run: `ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"`
2. Check the output
3. Only THEN ask questions or investigate further

Do not ask "what do you see" or "can you run this command" - just fix it.

---

## RULE 3: TEST CODE CHANGES BEFORE DEPLOYING

Before pushing any code change to production:

1. Check for syntax errors locally
2. Ensure indentation is correct (Python is sensitive to this)
3. If unsure, test with `python -m py_compile filename.py`

On 14 January 2026, multiple deployments failed due to syntax/indentation errors that should have been caught before pushing.

---

## RULE 4: READ THESE FILES AT SESSION START

At the start of EVERY session involving this project, read:

1. `CLAUDE_PROTOCOL.md` (this file) - mandatory rules
2. `CLAUDE_STARTUP_GUIDE.md` - system context and known issues
3. `CRASH_RECOVERY.md` - how to fix common problems

---

## RULE 5: SERVER DETAILS (for quick reference)

- **Server IP**: 167.172.54.56
- **SSH**: `ssh root@167.172.54.56`
- **Recovery**: `ssh root@167.172.54.56 "bash /opt/bms-analytics/recovery.sh"`
- **Dashboard**: https://cloud.birdlab.tech/
- **Filter**: https://cloud.birdlab.tech/filter/

---

## CONSEQUENCES OF IGNORING THIS PROTOCOL

The user has a PhD deadline and commercial commitments. Wasting their time with inefficient workflows directly impacts their ability to:
- Complete their research
- Secure funding
- Meet client commitments

This is not a hobby project. Treat it with appropriate urgency and efficiency.
