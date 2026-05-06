# Triage brief — INC00539734

**Reported by:** —
**Priority:** 4 - Low
**Created:** 2025-09-01 18:50:54

## What was reported

> Certaines de mes gestionnaires me remontent une problématique ponctuelle, à savoir que les partenaires qui apparaissent sur les factures ne sont pas conformes à

Certaines de mes gestionnaires me remontent une problématique ponctuelle, à savoir que les partenaires qui apparaissent sur les factures ne sont pas conformes à SAP._x000D_
Par exemple, dans les screens joints, on a sorti la facture 1 et 2 : RAS et lorsqu’elle sort la facture 3 (je précise que nous n’avons pas touché à SAP et encore moins aux partenaires). Le client facturé ne sort pas à la même adresse et pourtant c’est bien le même numéro client sur les 3 factures.

## Predicted routing

| Field | Top prediction | Confidence | 2nd | 3rd |
|---|---|---|---|---|
| Assignment group | `CUST.KONE.INT.SAP.ERP.AMS` | 64% | `KONE.SAP.Security.AMS` (33%) | `KONE.SAP.GRC.AMS` (3%) |
| Business service | `SAP Platform / Supportive` | 14% | `Controlling & Costing` (9%) | `Controls and Auditing` (8%) |

## Ranked root-cause hypotheses

These are derived from the close notes of historically similar incidents.

**1. Resolved - Configuration Changed** — similarity 0.30
> _SAP Société 399 Transaction VF04 trou dans le billing duelist_ (INC00663016)
> Close notes: Issue : VF04 issue._x000D_ _x000D_ Analysis : Due to EFS CR changes there was issue. CR changes reverted and contracts data updated by false saving the contracts. LSMW used.

**2. Solution provided** — similarity 0.27
> _BUG sur la TVA FRB ESCALIERS_ (INC00160444)
> Close notes: User manually changed Tax classification for material 8/8

**3. Resolved by caller** — similarity 0.27
> _Acompte NDB non reconnu_ (INC00479530)
> Close notes: Hi,_x000D_ _x000D_ Thank you for confirmation, since no action is needed marking it closed._x000D_ _x000D_ Thank you!!

**4. Resolved - Configuration Changed** — similarity 0.25
> _LES INFORMATIONS DE LA COMMANDE(VA) VENANT DE KTOC PSR NE FONCTIONNE PAS_ (INC00646779)
> Close notes: Issue : SAP PSR service order not updated._x000D_ _x000D_ Analysis : Issue fixed by manually updating order using Z_SD_R_U_SERVICE_UPDATE

**5. Solution provided** — similarity 0.24
> _terms and conditions to add to invoices_ (INC00532350)
> Close notes: no need of adding the terms and conditions for BEL and KDL company code, user confirmed to close the ticket


## Possible resolution paths

Based on the close codes of the 5 most similar past incidents:

- **Resolved - Configuration Changed** *(used in 2 of 5 matches)*
- **Solution provided** *(used in 2 of 5 matches)*
- **Resolved by caller** *(used in 1 of 5 matches)*

## KBA references

- **KB000A8238** (0.56) — ECM - Comment changer la langue dans l'application de bureau ECM

---
*Generated automatically. All hypotheses are evidence-grounded — verify before acting.*
