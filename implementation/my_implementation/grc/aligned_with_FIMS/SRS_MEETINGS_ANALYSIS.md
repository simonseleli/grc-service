# SRS Meetings Analysis — What the System Must Support

> Source: `grc-service/implementation/my_implementation/grc/SRS/AUDT2_ext.md`
> Section: 1.8.3 Conducting Internal Audit (Steps 14, 17, 20, 23–24)

---

## Overview

The SRS defines **4 distinct meeting types** during an audit engagement. They occur at different phases of the engagement lifecycle:

| # | Meeting Type | SRS Step | When It Happens | Who Arranges |
|---|-------------|----------|-----------------|--------------|
| 1 | **Entry Meeting** | Step 14 | After EN is issued, before fieldwork | LA |
| 2 | **Pre-exit Meeting** | Step 17 | After WPs are reviewed by LA, before CIA approval of WPs | LA |
| 3 | **Audit Team Meeting** | Step 20 | After CIA approves WPs, before draft report | LA |
| 4 | **Exit Meeting** | Steps 23–24 | After draft report is approved by CIA, with auditee | LA |

---

## Meeting 1: Entry Meeting (Step 14)

### SRS Text
> "LA arranges and conducts entry meeting with key process owners, record the attendance and proceedings of the meeting for future reference"

### When in workflow
- **After**: Engagement Notification (EN) is issued and sent to auditee (Steps 10–12)
- **Before**: Fieldwork / Working Papers begin (Step 15)

### Who is involved
- **Arranges**: Lead Auditor (LA)
- **Attendees**: Audit team + key process owners (auditees)

### What the system must capture
| Field | Required | Description |
|-------|----------|-------------|
| Meeting type | Yes | "Entry Meeting" |
| Meeting date | Yes | When the meeting was held |
| Participants/Attendance | Yes | List of attendees (names, roles, signatures/confirmation) |
| Proceedings/Minutes | Yes | Record of key discussions and decisions |
| Related engagement | Yes | Link to the audit engagement |

### Dependencies / Pre-conditions
- EN must be issued (approved by CIA with signature + QR code)
- EN must have been sent to auditee

### Outputs
- Entry Meeting Minutes (listed as a formal process output in SRS)
- Attendance register

### Checklist for verification
- [ ] Can LA create an Entry Meeting linked to an engagement?
- [ ] Can LA record the meeting date?
- [ ] Can LA record participants/attendance list?
- [ ] Can LA record meeting proceedings/minutes?
- [ ] Is the meeting type selectable (Entry Meeting)?
- [ ] Is Entry Meeting Minutes listed as a process output?

---

## Meeting 2: Pre-exit Meeting (Step 17)

### SRS Text
> "LA and Audit Team Members conducts pre-exit meeting at the audit area for clarification and communication of the result of the audit work."

### When in workflow
- **After**: LA reviews Working Papers and evidence (Step 16)
- **Before**: LA consolidates WP forms for CIA approval (Step 18)

### Who is involved
- **Arranges**: Lead Auditor (LA)
- **Attendees**: LA + Audit Team Members + Auditees (at the audit area)

### What the system must capture
| Field | Required | Description |
|-------|----------|-------------|
| Meeting type | Yes | "Pre-exit Meeting" |
| Meeting date | Yes | When the meeting was held |
| Participants | Yes | LA, team members, auditee representatives |
| Clarifications | Yes | Issues clarified during meeting |
| Agreed observations | Yes | Observations agreed upon between auditors and auditee |
| Related engagement | Yes | Link to the audit engagement |

### Dependencies / Pre-conditions
- Working Papers must have been reviewed by LA (Step 16)
- This is specifically about clarifying audit results with the auditee

### Purpose
- Communicate preliminary audit results to auditee
- Get clarification on any unclear findings
- Agree on observations before formal documentation

### SRS General Requirements section says:
> **Pre-Exit Meeting** — The system shall support scheduling and documentation of pre-exit meetings.
> **Dependencies**: Working papers reviewed
> **Key Information Required**: Clarifications, Agreed observations

### Checklist for verification
- [ ] Can LA create a Pre-exit Meeting linked to an engagement?
- [ ] Can LA record clarifications discussed?
- [ ] Can LA record agreed observations?
- [ ] Can LA record participants?
- [ ] Does the system enforce that WPs were reviewed before pre-exit meeting? (nice-to-have, not strictly required)

---

## Meeting 3: Audit Team Meeting (Step 20)

### SRS Text
> "LA arranges and conducts Audit team meeting prior to the exit meeting with auditee management for reviewing and consolidating the deviations and recommendations for presentation to the auditee and for preparation of the draft Internal Audit Report"

### When in workflow
- **After**: CIA reviews and approves working paper forms (Step 19)
- **Before**: Draft Internal Audit Report is prepared (Step 21)

### Who is involved
- **Arranges**: Lead Auditor (LA)
- **Attendees**: Internal audit team only (LA + Audit Team Members) — **NO auditees**

### What the system must capture
| Field | Required | Description |
|-------|----------|-------------|
| Meeting type | Yes | "Audit Team Meeting" |
| Meeting date | Yes | When the meeting was held |
| Participants | Yes | LA + audit team members only |
| Deviations reviewed | Yes | List of deviations/findings consolidated |
| Recommendations | Yes | Recommendations consolidated for presentation |
| Minutes | Yes | Record of discussions |
| Related engagement | Yes | Link to the audit engagement |

### Purpose
- Internal audit team reviews and consolidates ALL deviations and recommendations
- Prepares presentation for the exit meeting with auditee
- Serves as preparation ground for the draft Internal Audit Report

### Dependencies / Pre-conditions
- CIA must have approved the consolidated working papers (Step 19)

### Checklist for verification
- [ ] Can LA create an Audit Team Meeting linked to an engagement?
- [ ] Can LA record which deviations/recommendations were reviewed?
- [ ] Is this meeting type restricted to internal audit team (no auditees)?
- [ ] Does this meeting precede the draft report preparation?

---

## Meeting 4: Exit Meeting (Steps 23–24)

### SRS Text
> Step 23: "LA arranges exit meeting by sending Exit meeting Notification including draft audit report to auditee, auditors and other personnel responsible for the finding"
>
> Step 24: "LA conducts Exit meeting with the key personnel of the audited activity and document exit meeting minutes and attendance sheet"

### When in workflow
- **After**: Draft report is reviewed by LA and approved by CIA (Steps 21–22)
- **Before**: Final report preparation (Steps 12–13 in the second flow)

### Who is involved
- **Arranges**: Lead Auditor (LA)
- **Attendees**: Auditee management + auditors + other personnel responsible for findings

### What the system must capture
| Field | Required | Description |
|-------|----------|-------------|
| Meeting type | Yes | "Exit Meeting" |
| Meeting date | Yes | When the meeting was held |
| Participants/Attendance | Yes | Attendance sheet with names and roles |
| Exit Meeting Notification | Yes | Formal notification sent to auditee (includes draft report) |
| Draft audit report attached | Yes | The draft report must be shared with the notification |
| Minutes | Yes | Exit meeting minutes documenting discussions |
| Related engagement | Yes | Link to the audit engagement |

### Dependencies / Pre-conditions
- Draft Internal Audit Report must be prepared and approved by CIA (Steps 21–22)
- CIA must have authorized LA to proceed with the exit meeting

### Outputs
- Exit Meeting Minutes (listed as a formal process output in SRS)
- Attendance sheet

### SRS General Requirements section says:
> **Exit Meeting** — The system shall enable LA to:
> - Send Exit Meeting Notification with draft audit report
> - Conduct exit meeting with auditee management
> - Record attendance and minutes
>
> **Data Requirements**: Exit meeting notification, Exit meeting minutes, Attendance register

### Checklist for verification
- [ ] Can LA create an Exit Meeting linked to an engagement?
- [ ] Can LA send an Exit Meeting Notification?
- [ ] Can the draft audit report be attached to the notification?
- [ ] Can LA record attendance (attendance sheet)?
- [ ] Can LA record exit meeting minutes?
- [ ] Is Exit Meeting Minutes listed as a process output?

---

## Summary: Complete Meeting Workflow in Order

```
EN Issued (Steps 10-12)
    │
    ▼
┌─────────────────────────────┐
│ 1. ENTRY MEETING (Step 14)  │  LA + Auditees
│    - Attendance              │  "Getting started" meeting
│    - Proceedings/Minutes     │
└─────────────┬───────────────┘
              │
    Fieldwork: Working Papers (Step 15)
    LA Reviews WPs (Step 16)
              │
              ▼
┌──────────────────────────────────┐
│ 2. PRE-EXIT MEETING (Step 17)   │  LA + Team + Auditees
│    - Clarifications              │  "Here's what we found" meeting
│    - Agreed observations         │
└─────────────┬────────────────────┘
              │
    LA Consolidates WPs (Step 18)
    CIA Approves WPs (Step 19)
              │
              ▼
┌──────────────────────────────────────┐
│ 3. AUDIT TEAM MEETING (Step 20)     │  Audit Team ONLY (no auditees)
│    - Review deviations               │  "Let's align before exit" meeting
│    - Consolidate recommendations     │
│    - Prepare for draft report        │
└─────────────┬────────────────────────┘
              │
    Draft Report Prepared (Step 21)
    LA + CIA Review Draft (Step 22)
              │
              ▼
┌──────────────────────────────────────────┐
│ 4. EXIT MEETING (Steps 23-24)            │  LA + Auditees + responsible personnel
│    - Exit Meeting Notification sent      │  "Formal results presentation" meeting
│    - Draft report attached               │
│    - Attendance sheet                    │
│    - Exit meeting minutes                │
└──────────────────────────────────────────┘
              │
    Final Report (Steps 12-13)
```

---

## Data Model Requirements (from SRS)

A Meeting record should support at minimum:

| Field | Type | Notes |
|-------|------|-------|
| `meeting_type` | Choice | entry_meeting, pre_exit_meeting, audit_team_meeting, exit_meeting |
| `engagement` | FK | Link to the parent Audit Engagement |
| `meeting_date` | DateTime | When the meeting occurred |
| `location` | Text | Where it was held (audit area for pre-exit, office, etc.) |
| `participants` | M2M or JSON | Attendees with names, roles, signatures |
| `minutes` | Text/RichText | Meeting proceedings/minutes |
| `clarifications` | Text | Specific to pre-exit meeting |
| `agreed_observations` | Text | Specific to pre-exit meeting |
| `notification_sent` | Boolean | Whether formal notification was sent (entry + exit) |
| `notification_date` | DateTime | When notification was sent |
| `attachments` | Files | Draft report (exit), EN (entry), etc. |
| `created_by` | FK User | Who created the record (should be LA) |

### Meeting Type Constraints

| Meeting Type | Auditees Attend? | Notification Required? | Key Attachment |
|-------------|-----------------|----------------------|----------------|
| Entry Meeting | Yes | EN already sent | EN copy |
| Pre-exit Meeting | Yes | No formal notification in SRS | None |
| Audit Team Meeting | **No** (internal only) | No | None |
| Exit Meeting | Yes | **Yes** (Exit Meeting Notification) | **Draft audit report** |

---

## Process Outputs (from SRS)

The SRS explicitly lists these as formal outputs of the "Conducting Internal Audit" process:
1. ✅ Engagement Audit Report
2. ✅ **Entry Meeting Minutes**
3. ✅ **Exit Meeting Minutes**

Note: Pre-exit meeting notes and Audit Team meeting notes are not listed as formal outputs, but the SRS still requires they be captured and documented.
