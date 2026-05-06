# Runbook — INC00643802

> **Scope:** Initial triage only. Escalate before performing any change that touches a production system.

## 1. Acknowledge

- [ ] Set ticket state to **In Progress** in your ITSM tool.
- [ ] Add a brief comment on the ticket: *"Picking this up, will revert with findings."*

## 2. Reproduce / verify

- [ ] Re-read the user's `short_description` and `description`.
- [ ] If the issue is reproducible, capture: timestamp, user ID, transaction code, error message text, and a screenshot if user provided one.
- [ ] **Do not** ask the user to re-run anything destructive. Read-only retries only.

## 3. Check known causes (from similar incidents)

- [ ] **Hypothesis 1** — *Resolved - Training/Guidance Provided*. Similar to INC00613311. Look for the symptoms described in:
  > Issue(Question/Problem):?????????????????_x000D_ Root cause(Reason):???????????PO
- [ ] **Hypothesis 2** — *Resolved - Training/Guidance Provided*. Similar to INC00633493. Look for the symptoms described in:
  > Issue(Question/Problem): ???????????PO,?????????????PO,???_x000D_ Root cause(Reason):PR??????_x000D_ Solution (Workaround/Answer):?PR???????MRP_x000D_ T-code(Program):ME52N
- [ ] **Hypothesis 3** — *Resolved - Training/Guidance Provided*. Similar to INC00613412. Look for the symptoms described in:
  > SAP Z04 system was restarted completely on 3rd Dec. due to restart system was slow. next runs are fine and improving.

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
