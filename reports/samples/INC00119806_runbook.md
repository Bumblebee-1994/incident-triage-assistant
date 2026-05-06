# Runbook — INC00119806

> **Scope:** Initial triage only. Escalate before performing any change that touches a production system.

## 1. Acknowledge

- [ ] Set ticket state to **In Progress** in your ITSM tool.
- [ ] Add a brief comment on the ticket: *"Picking this up, will revert with findings."*

## 2. Reproduce / verify

- [ ] Re-read the user's `short_description` and `description`.
- [ ] If the issue is reproducible, capture: timestamp, user ID, transaction code, error message text, and a screenshot if user provided one.
- [ ] **Do not** ask the user to re-run anything destructive. Read-only retries only.

## 3. Check known causes (from similar incidents)

- [ ] **Hypothesis 1** — *Solution provided*. Similar to INC00201314. Look for the symptoms described in:
  > The share point has been expired due to upload to share point is getting failed. Now, we have created a new share point app with the help of o365 team. Now, the upload file to s...
- [ ] **Hypothesis 2** — *Resolved - Configuration Changed*. Similar to INC00584629. Look for the symptoms described in:
  > Hi aprajitha,_x000D_ _x000D_ We can update and configure the folders from RMJ for job execution, once the file is saved on Sharepoint you can move it to the required folder._x00...
- [ ] **Hypothesis 3** — *Solution provided*. Similar to INC00343529. Look for the symptoms described in:
  > The Issue has been resolved now. From the next run the spool will upload to SharePoint.

## 4. Apply KBA if applicable

- [ ] No KBA above the confidence threshold. Search the KB manually if needed.

## 5. Safe diagnostics (no impact)

- [ ] Check user authorizations / role assignments via SU01 (read-only).
- [ ] Check transaction logs / system messages relevant to the reported transaction.
- [ ] Confirm the user's client, system, and country code match the affected business service: `Accounting & Statutory Reporting`.

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
