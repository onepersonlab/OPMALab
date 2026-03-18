# 🔐 Permission Matrix · SciLab-Agents

> **Not "send whenever you want" — real checks and balances.**

This document defines the communication permissions between all roles in SciLab-Agents. Violations are automatically intercepted and logged.

---

## 📊 Permission Matrix

### Message Sending Permissions

| From ↓ → To | Lab Director | Planning | Review | Operations | CS | Chem | Bio | Mat | Med | Agr | Env | Eng |
|-------------|--------------|----------|--------|------------|----|------|-----|-----|-----|-----|-----|-----|
| **PI-Principal** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Lab Director** | — | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Planning Office** | ❌ | — | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Review Board** | ❌ | ✅ (Veto) | — | ✅ (Approve) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Operations Office** | ✅ (Report) | ❌ | ❌ | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PIs** | ❌ | ❌ | ❌ | ✅ (Progress) | — | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 📜 Permission Rules

### Rule 1: PI-Principal Direct Access
**PI-Principal communicates ONLY with Lab Director.**

- ✅ PI-Principal → Lab Director: All research directives
- ❌ PI-Principal → Any other role: Intercepted

**Rationale**: Lab Director is the single point of triage. This prevents:
- Overloading execution agents with casual queries
- Bypassing the planning and review process
- Inconsistent task creation

---

### Rule 2: Single-Direction Flow
**Tasks flow in one direction: Lab Director → Planning → Review → Operations → PIs**

| Transition | Allowed | Notes |
|------------|---------|-------|
| Lab Director → Planning | ✅ | Directive forwarding |
| Planning → Review | ✅ | Plan submission |
| Review → Operations | ✅ | Plan approval |
| Review → Planning | ✅ | Veto (with feedback) |
| Operations → PIs | ✅ | Task assignment |
| PIs → Operations | ✅ | Progress reports |
| Operations → Lab Director | ✅ | Final report |
| Lab Director → PI-Principal | ✅ | Final reply |

**Reverse flows are NOT allowed** (except veto):
- ❌ PIs → Planning (must go through Operations)
- ❌ Planning → Operations (must go through Review)
- ❌ Operations → Review (only Review → Operations)

---

### Rule 3: Review Board Veto Power
**Review Board can veto Planning Office plans.**

| Action | Allowed | Requirements |
|--------|---------|--------------|
| Approve → Operations | ✅ | Plan meets quality standards |
| Veto → Planning | ✅ | Must include specific feedback |
| Veto → Operations | ❌ | Cannot veto after approval |
| Veto → PIs | ❌ | No direct communication |

**Veto Requirements**:
1. Must specify exact issues (not vague criticism)
2. Must provide actionable modification suggestions
3. Must reference specific sub-tasks or sections

---

### Rule 4: No Cross-PI Communication
**PIs communicate ONLY with Operations Office.**

- ✅ PI → Operations: Progress reports, deliverable submissions, blocker notifications
- ❌ PI → PI: Intercepted (must coordinate through Operations)
- ❌ PI → Planning/Review: Intercepted

**Rationale**: Operations Office is the single coordinator. This ensures:
- Centralized progress tracking
- Conflict resolution by designated coordinator
- Consistent consolidation of results

---

### Rule 5: Report Channel
**Only Operations Office reports final results to Lab Director.**

- ✅ Operations → Lab Director: Final consolidated report
- ❌ PIs → Lab Director: Intercepted
- ❌ PIs → PI-Principal: Intercepted

**Rationale**: Lab Director receives unified report, not fragmented PI updates.

---

### Rule 6: Escalation Path
**Issues escalate through designated channels only.**

```
PI → Operations Office → Lab Director → PI-Principal (if critical)
```

| Issue Level | Handler |
|-------------|---------|
| Task blocker | Operations Office |
| Cross-PI conflict | Operations Office |
| Plan quality concern | Review Board |
| Critical project risk | Lab Director → PI-Principal |

---

## 🚨 Violation Handling

### Automatic Interception
The system automatically intercepts permission violations:

```
[INTERCEPTED] Message from pi_cs to pi_chem
Reason: Direct PI-to-PI communication not allowed
Action: Route through Operations Office
```

### Violation Log
All violations are logged for audit:
```json
{
  "timestamp": "2026-03-18T15:30:00Z",
  "from": "pi_cs",
  "to": "pi_chem",
  "violation": "Direct PI-to-PI communication",
  "action": "Intercepted and logged"
}
```

### Repeated Violations
- 1st violation: Warning + automatic reroute
- 2nd violation: Warning to role supervisor
- 3rd violation: Escalate to Lab Director

---

## 📋 Communication Templates

### Allowed: Lab Director → Planning Office
```
📋 Lab Director · Directive Forward
Task ID: SLC-xxx
PI-Principal Original: [original text]
Summarized Requirements:
  - Goal: [one sentence]
  - Requirements: [specific requirements]
  - Expected Output: [deliverable description]
```

### Allowed: Planning → Review Board
```
📋 Planning Office · Plan Submission
Task ID: SLC-xxx
Plan Summary: [...]
Sub-task Details: [...]
Dependencies: [...]
Risk Assessment: [...]
```

### Allowed: Review Board → Planning (Veto)
```
📋 Review Board · Veto
Task ID: SLC-xxx
Decision: 🚫 VETOED

Veto Reasons:
1. [Specific issue]
   - Problem: [description]
   - Required Fix: [what to change]

Modification Suggestions:
- [Concrete suggestion]
```

### Allowed: Review Board → Operations (Approve)
```
📋 Review Board · Approval
Task ID: SLC-xxx
Decision: ✅ APPROVED
Review Summary: [brief comment]
```

### Allowed: Operations → PIs
```
📋 Operations Office · Task Assignment
Task ID: SLC-xxx-T01
Assigned PI: pi_cs
Deliverable: [Specific output]
Deadline: [Date/Time]
Dependencies: [None | Wait for SLC-xxx-T02]
Priority: [High/Medium/Low]
```

### Allowed: PIs → Operations
```
📋 PI-CS · Deliverable Submission
Task ID: SLC-xxx-T01
Status: ✅ Completed
Deliverable: [Description]
Summary: [2-3 sentences]
Key Findings: [...]
```

### Allowed: Operations → Lab Director
```
📋 Operations Office · Final Report
Task ID: SLC-xxx
Status: ✅ COMPLETED
Executive Summary: [...]
Deliverables: [...]
Key Findings: [...]
```

---

## 🔬 Role Reference

| SciLab Role | Agent ID | Original Role |
|-------------|----------|---------------|
| Lab Director | `lab_director` | 太子 |
| Planning Office | `planning_office` | 中书省 |
| Review Board | `review_board` | 门下省 |
| Operations Office | `operations_office` | 尚书省 |
| PI, Computer Science | `pi_cs` | 兵部 (CS) |
| PI, Chemistry | `pi_chem` | 工部 (Chem) |
| PI, Biology | `pi_bio` | 工部 (Bio) |
| PI, Materials | `pi_mat` | 工部 (Mat) |
| PI, Medicine | `pi_med` | 工部 (Med) |
| PI, Agriculture | `pi_agr` | 户部 (Agr) |
| PI, Environmental | `pi_env` | 户部 (Env) |
| PI, Engineering | `pi_eng` | 工部 (Eng) |

---

## 📊 Permission Matrix Visualization

```
                    ┌──────────────────────────────────────────────────┐
                    │              PI-Principal                        │
                    │         (Feishu / Telegram / Signal)             │
                    └────────────────────┬─────────────────────────────┘
                                         │ ✅ Directive
                                         ▼
                    ┌──────────────────────────────────────────────────┐
                    │              Lab Director                        │
                    │         (Triage & Forward)                       │
                    └────────────────────┬─────────────────────────────┘
                                         │ ✅ Forward
                                         ▼
                    ┌──────────────────────────────────────────────────┐
                    │           Planning Office                        │
                    │         (Plan & Decompose)                       │
                    └────────────────────┬─────────────────────────────┘
                                         │ ✅ Submit
                                         ▼
                    ┌──────────────────────────────────────────────────┐
                    │            Review Board                          │
                    │    (Approve ✅ / Veto 🚫)                        │
                    └────────┬───────────────────────┬─────────────────┘
                             │ ✅ Approve            │ 🚫 Veto
                             ▼                       ▼
                    ┌─────────────────┐     ┌─────────────────┐
                    │  Operations     │     │   Planning      │
                    │    Office       │     │    Office       │
                    │  (Coordinate)   │     │  (Revise)       │
                    └────────┬────────┘     └─────────────────┘
                             │ ✅ Assign
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌─────────────┐  ┌─────────────┐   ┌─────────────┐
    │   PI-CS     │  │   PI-Chem   │   │   PI-Bio    │
    └──────┬──────┘  └──────┬──────┘   └──────┬──────┘
           │                │                  │
           └────────────────┼──────────────────┘
                            │ ✅ Report
                            ▼
                    ┌─────────────────┐
                    │  Operations     │
                    │    Office       │
                    │ (Consolidate)   │
                    └────────┬────────┘
                             │ ✅ Final Report
                             ▼
                    ┌─────────────────┐
                    │  Lab Director   │
                    │ (Reply to PI)   │
                    └────────┬────────┘
                             │ ✅ Reply
                             ▼
                    ┌─────────────────┐
                    │  PI-Principal   │
                    └─────────────────┘
```

---

## 📝 Notes

1. **Permission enforcement is automatic** — The system intercepts violations before delivery.
2. **Audit trail is complete** — All messages (allowed and intercepted) are logged.
3. **Exceptions require Lab Director approval** — Emergency communications must be approved by Lab Director.
4. **Matrix is configurable** — Adjust permissions by editing this file and updating system config.

---

> ⚖️ **Checks and balances are not obstacles — they are guarantees of quality.**
> 
> *制衡非阻碍，乃质量之保障*
