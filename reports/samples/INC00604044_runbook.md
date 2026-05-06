# Runbook — INC00604044

> **Scope:** Initial triage only. Escalate before performing any change that touches a production system.

## 1. Acknowledge

- [ ] Set ticket state to **In Progress** in your ITSM tool.
- [ ] Add a brief comment on the ticket: *"Picking this up, will revert with findings."*

## 2. Reproduce / verify

- [ ] Re-read the user's `short_description` and `description`.
- [ ] If the issue is reproducible, capture: timestamp, user ID, transaction code, error message text, and a screenshot if user provided one.
- [ ] **Do not** ask the user to re-run anything destructive. Read-only retries only.

## 3. Check known causes (from similar incidents)

- [ ] **Hypothesis 1** — *Solution provided*. Similar to INC00140035. Look for the symptoms described in:
  > Close it first.
- [ ] **Hypothesis 2** — *Workaround provided*. Similar to INC00102730. Look for the symptoms described in:
  > Already done it.
- [ ] **Hypothesis 3** — *Resolved as Service Request*. Similar to INC00604929. Look for the symptoms described in:
  > Resolved.

## 4. Apply KBA if applicable

- [ ] No KBA above the confidence threshold. Search the KB manually if needed.

## 5. Safe diagnostics (no impact)

- [ ] Check user authorizations / role assignments via SU01 (read-only).
- [ ] Check transaction logs / system messages relevant to the reported transaction.
- [ ] Confirm the user's client, system, and country code match the affected business service: `SAP Platform / Supportive`.

## 6. Decision point

- [ ] If hypothesis confirmed → apply standard fix and record close code.
- [ ] If unclear → escalate to **CUST.KONE.INT.SAP.ERP.AMS** with all collected evidence.
- [ ] If multiple users impacted → raise to a **major incident** review before any change.

## 7. Close-out

- [ ] Add resolution summary to `close_notes`.
- [ ] Pick a `close_code` from the standard list (e.g. *Solution provided*, *Resolved by request*, *Workaround provided*).
- [ ] Confirm with the user before closing.

---
*All steps above are intentionally generic and non-destructive. This runbook is a checklist, not an automation.*
