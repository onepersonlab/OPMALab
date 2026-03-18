# 🧪 SciLab-Agents

## AI-Driven Multi-Discipline Research Collaboration Platform

A multi-agent system for interdisciplinary scientific research, inspired by the ancient Chinese "Three Departments and Six Ministries" governance model. Each agent is a specialized researcher with defined expertise, communication protocols, and deliverables.

**12 AI Agents** (4 coordination roles + 8 discipline PIs) form a complete research workflow: Lab Director triages, Planning Office designs, Review Board approves, Operations Office coordinates, and 8 Discipline PIs execute.

More **institutional oversight** than CrewAI, more **real-time visibility** than AutoGen.

---

## 🚀 Quick Start

### Option 1: Auto-Configure with OpenClaw (Recommended)

**No code. No commands. Just conversation.**

#### Step 1: Set up OpenClaw
Configure your OpenClaw system following the official documentation.

#### Step 2: Start a Conversation
Initiate a chat with the Lab Director agent and provide your research goal:

```
I want to build an AI-driven drug discovery platform.
I need expertise in chemistry, biology, computer science, and medicine.
```

#### Step 3: Lab Director Triage
The Lab Director will:
- Triage your message (casual Q&A vs. formal research directive)
- For complex directives: summarize and forward to Planning Office

#### Step 4: Planning → Review → Execution
```
Lab Director → Planning Office → Review Board → Operations Office → 8 PIs
```

#### Step 5: Receive Final Report
Operations Office consolidates all PI deliverables and reports back through Lab Director.

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              PI-Principal (You / "Emperor")             │
│                    Feishu / Telegram                    │
└─────────────────────────┬───────────────────────────────┘
                          │ Research Directive
┌─────────────────────────▼───────────────────────────────┐
│              🎓 Lab Director (taizi)                    │
│         Triage: Casual→Reply / Directive→Task           │
└─────────────────────────┬───────────────────────────────┘
                          │ Forward Directive
┌─────────────────────────▼───────────────────────────────┐
│           📋 Planning Office (zhongshu)                 │
│      Receive → Plan → Decompose → Submit for Review     │
└─────────────────────────┬───────────────────────────────┘
                          │ Submit Plan
┌─────────────────────────▼───────────────────────────────┐
│           🔍 Review Board (menxia)                      │
│        Review → Approve ✅ / Veto 🚫 (with feedback)    │
└─────────────────────────┬───────────────────────────────┘
                          │ Approved Plan
┌─────────────────────────▼───────────────────────────────┐
│          📮 Operations Office (shangshu)                │
│     Assign → Coordinate → Monitor → Consolidate → Report│
└───┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────┘
    │      │      │      │      │      │      │      │
┌───▼──┐┌──▼───┐┌─▼────┐┌─▼────┐┌─▼────┐┌─▼────┐┌─▼────┐┌─▼────┐
│PI-CS ││PI-Chem││PI-Bio││PI-Mat││PI-Med││PI-Agr││PI-Env││PI-Eng│
│  CS  ││ Chem ││ Bio  ││ Mat  ││ Med  ││ Agr  ││ Env  ││ Eng  │
└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘
```

### Coordination Roles

| Role | Agent ID | Responsibility |
|------|----------|----------------|
| 🎓 **Lab Director** | `lab_director` | Message triage, task creation, final reply to PI-Principal |
| 📋 **Planning Office** | `planning_office` | Receive directives, design research plans, decompose into sub-tasks |
| 🔍 **Review Board** | `review_board` | Quality gate: approve or veto plans (with feedback) |
| 📮 **Operations Office** | `operations_office` | Task assignment, coordination, progress monitoring, consolidation |

### Discipline PIs

| Discipline | Agent ID | Expertise |
|------------|----------|-----------|
| 🖥️ Computer Science | `pi_cs` | AI/ML, Software Engineering, Data Systems |
| 🧪 Chemistry | `pi_chem` | Organic, Inorganic, Analytical, Computational Chemistry |
| 🧬 Biology | `pi_bio` | Molecular Biology, Genetics, Bioinformatics |
| 🔩 Materials Science | `pi_mat` | Nanomaterials, Polymers, Composites |
| 🏥 Medicine | `pi_med` | Drug Discovery, Clinical Research, Medical Imaging |
| 🌾 Agriculture | `pi_agr` | Crop Science, Precision Agriculture, Food Security |
| 🌍 Environmental Science | `pi_env` | Climate, Ecology, Pollution, Sustainability |
| ⚙️ Engineering | `pi_eng` | Mechanical, Electrical, Chemical, Civil Engineering |

---

## 🔐 Permission Matrix

**Not "send whenever you want" — real checks and balances.**

| From ↓ → To | Lab Director | Planning | Review | Operations | PIs |
|-------------|--------------|----------|----------|------------|-----|
| **PI-Principal** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Lab Director** | — | ✅ | ❌ | ❌ | ❌ |
| **Planning Office** | ❌ | — | ✅ | ❌ | ❌ |
| **Review Board** | ❌ | ✅ (Veto) | — | ✅ (Approve) | ❌ |
| **Operations Office** | ✅ (Report) | ❌ | ❌ | — | ✅ |
| **PIs** | ❌ | ❌ | ❌ | ✅ (Progress) | ❌ |

### Key Rules:
1. **PI-Principal → Lab Director only**: All directives flow through Lab Director
2. **Single-direction flow**: Lab Director → Planning → Review → Operations → PIs
3. **Veto power**: Review Board can veto Planning Office (must provide feedback)
4. **No cross-PI communication**: PIs coordinate only through Operations Office
5. **Report channel**: Only Operations Office reports final results to Lab Director

---

## 📊 Task State Machine

```
[Triage] → [Planning] → [Review] → [Approved] → [Execution] → [Consolidation] → [✅ Complete]
              ↑            ↑            ↑
              │            │            │
              └──── Veto ──┘            │
                                        │
              ┌──────── Cancel/Stop ────┘
```

---

## 🛠 Installation

### Prerequisites
- OpenClaw installed and configured
- Python 3.9+
- macOS / Linux

### Clone and Setup
```bash
cd /home/auto/.openclaw/workspace-taizi
git clone https://github.com/ingeniousfrog/edict-20260301.git scilab-agents
cd scilab-agents

# The agents directory already contains all 12 SOUL.md files
# for SciLab configuration
```

### Register Agents (Manual)
Add each agent to your OpenClaw configuration:
```bash
# Example: Register Lab Director
# (Use your OpenClaw agent registration command)
```

### Start Dashboard
```bash
# Terminal 1: Data refresh loop
bash scripts/run_loop.sh

# Terminal 2: Dashboard server
python3 dashboard/server.py

# Open browser
open http://127.0.0.1:7891
```

---

## 📋 Kanban Commands

```bash
# Create task
python3 scripts/kanban_update.py create SLC-YYYYMMDD-NNN "Title" State Org Official

# Update state
python3 scripts/kanban_update.py state SLC-xxx State "Description"

# Flow transition
python3 scripts/kanban_update.py flow SLC-xxx "From" "To" "Remark"

# Mark done
python3 scripts/kanban_update.py done SLC-xxx "Output" "Summary"

# Report progress
python3 scripts/kanban_update.py progress SLC-xxx "Current action" "Plan1✅|Plan2🔄|Plan3"
```

---

## 📝 Example: Drug Discovery Project

### PI-Principal Directive:
```
I want to discover new drug candidates for Alzheimer's disease.
Focus on: target identification, compound screening, and ADME-Tox prediction.
```

### Flow:
1. **Lab Director**: Triage → Create task SLC-20260318-001 → Forward to Planning
2. **Planning Office**: Design plan with 4 sub-tasks:
   - T01 (pi_med): Target identification & validation
   - T02 (pi_chem): Compound library screening
   - T03 (pi_cs): ML-based ADME-Tox prediction model
   - T04 (pi_bio): In vitro validation assays
3. **Review Board**: Review → Approve ✅
4. **Operations Office**: Assign to 4 PIs → Monitor → Consolidate
5. **Final Report**: Integrated findings with recommendations

---

## 🎬 Demo

See `docs/` for demo videos and screenshots.

---

## 📁 File Structure

```
scilab-agents/
├── agents/
│   ├── lab_director/SOUL.md    # Lab Director · Triage
│   ├── planning_office/SOUL.md # Planning Office · Strategy
│   ├── review_board/SOUL.md    # Review Board · Quality Gate
│   ├── operations_office/SOUL.md # Operations Office · Coordination
│   ├── pi_cs/SOUL.md           # PI, Computer Science
│   ├── pi_chem/SOUL.md         # PI, Chemistry
│   ├── pi_bio/SOUL.md          # PI, Biology
│   ├── pi_mat/SOUL.md          # PI, Materials Science
│   ├── pi_med/SOUL.md          # PI, Medicine
│   ├── pi_agr/SOUL.md          # PI, Agriculture
│   ├── pi_env/SOUL.md          # PI, Environmental Science
│   └── pi_eng/SOUL.md          # PI, Engineering
├── dashboard/
│   ├── dashboard.html          # Kanban UI
│   └── server.py               # API Server
├── scripts/
│   ├── kanban_update.py        # Kanban CLI
│   └── run_loop.sh             # Data refresh loop
├── protocols/
│   └── permissions.md          # Permission matrix (create this)
├── docs/                       # Documentation & screenshots
└── README.md                   # This file
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

### Welcome Contributions:
- 🎨 UI enhancements (dark/light theme, responsive design)
- 🤖 New discipline PIs (Physics, Mathematics, etc.)
- 📦 Domain-specific skills for each PI
- 🔗 Integrations (Notion, Jira, GitHub Issues, Electronic Lab Notebooks)
- 🌐 Internationalization
- 📱 Mobile responsiveness

---

## 📊 Comparison with OnePersonLab

| Dimension | OnePersonLab | SciLab-Agents |
|-----------|--------------|---------------|
| **Core Roles** | Lab-Director (single coordinator) | 4-tier coordination (checks & balances) |
| **Review Mechanism** | ❌ No dedicated review | ✅ Review Board with veto power |
| **Message Triage** | ❌ All messages create tasks | ✅ Lab Director triage (casual→reply) |
| **Permission Control** | ❌ Flat communication | ✅ Strict permission matrix |
| **Real-time Kanban** | ⚠️ Basic | ✅ Full Kanban + timeline + interventions |
| **Task Intervention** | ❌ Not intervenable | ✅ Stop/Cancel/Resume |
| **Audit Trail** | ⚠️ Partial | ✅ Complete memorial archive |
| **Disciplines** | 11 (242 agents) | 8 (12 core agents) |
| **Use Case** | Large-scale research teams | Lean, efficient research collaboration |

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Inspired by the ancient Chinese "Three Departments and Six Ministries" (三省六部制) governance system
- Built on [OpenClaw](https://openclaw.ai) multi-agent framework
- Original concept from [edict-20260301](https://github.com/ingeniousfrog/edict-20260301)

---

> 🧪 **Governing research with the wisdom of ancient empires**
> 
> *以古制御新技，以智慧驾驭 AI*
