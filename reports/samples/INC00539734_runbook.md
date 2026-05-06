# Runbook — INC00539734

> **Scope:** Initial triage only. Escalate before performing any change that touches a production system.

## 1. Acknowledge

- [ ] Set ticket state to **In Progress** in your ITSM tool.
- [ ] Add a brief comment on the ticket: *"Picking this up, will revert with findings."*

## 2. Reproduce / verify

- [ ] Re-read the user's `short_description` and `description`.
- [ ] If the issue is reproducible, capture: timestamp, user ID, transaction code, error message text, and a screenshot if user provided one.
- [ ] **Do not** ask the user to re-run anything destructive. Read-only retries only.

## 3. Check known causes (from similar incidents)

- [ ] **Hypothesis 1** — *Resolved - Configuration Changed*. Similar to INC00663016. Look for the symptoms described in:
  > Issue : VF04 issue._x000D_ _x000D_ Analysis : Due to EFS CR changes there was issue. CR changes reverted and contracts data updated by false saving the contracts. LSMW used.
- [ ] **Hypothesis 2** — *Solution provided*. Similar to INC00160444. Look for the symptoms described in:
  > User manually changed Tax classification for material 8/8
- [ ] **Hypothesis 3** — *Resolved by caller*. Similar to INC00479530. Look for the symptoms described in:
  > Hi,_x000D_ _x000D_ Thank you for confirmation, since no action is needed marking it closed._x000D_ _x000D_ Thank you!!

## 4. Apply KBA if applicable

- [ ] Review **KB000A8238** — ECM - Comment changer la langue dans l'application de bureau ECM.
- [ ] Walk through the KBA steps in a non-production environment first if possible.

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
