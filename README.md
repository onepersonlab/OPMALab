# 🧪 SciLab-Agents

## AI-Driven Multi-Discipline Research Collaboration Platform

A multi-agent system for interdisciplinary scientific research, inspired by the ancient Chinese "Three Departments and Six Ministries" governance model. Each agent is a specialized researcher with defined expertise, communication protocols, and deliverables.

**12 AI Agents** (4 coordination roles + 8 discipline PIs) form a complete research workflow: Lab Director triages, Planning Office designs, Review Board approves, Operations Office coordinates, and 8 Discipline PIs execute.

More **institutional oversight** than CrewAI, more **real-time visibility** than AutoGen.

<p align="center">
  <a href="#-quick-start">🚀 Quick Start</a> ·
  <a href="#-architecture">🏛️ Architecture</a> ·
  <a href="#-installation">📦 Installation</a> ·
  <a href="#-usage">📝 Usage</a> ·
  <a href="#-examples">💡 Examples</a> ·
  <a href="#-comparison">📊 Comparison</a> ·
  <a href="#-contributing">🤝 Contributing</a>
</p>

---

## 🚀 Quick Start

### Option 1: One-Click Installation (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/onepersonlab/onepersonlab-agents.git
cd onepersonlab-agents

# 2. Run installer
chmod +x install.sh && ./install.sh

# 3. Start services
bash scripts/run_loop.sh &
python3 dashboard/server.py

# 4. Open dashboard
open http://127.0.0.1:7891
```

### Option 2: Docker Demo

```bash
docker run -p 7891:7891 onepersonlab/scilab-agents:latest
open http://localhost:7891
```

### Option 3: Conversation-Based Setup

**No commands. Just talk.**

1. Configure OpenClaw with your preferred messaging channel (Feishu/Telegram/Signal)
2. Send a message to Lab Director:
   ```
   I want to build an AI-driven drug discovery platform.
   I need expertise in chemistry, biology, computer science, and medicine.
   ```
3. Lab Director will triage and coordinate the team automatically

---

## 🏛️ Architecture

### Workflow

```
┌─────────────────────────────────────────────────────────┐
│              PI-Principal (You / "Emperor")             │
│                    Feishu / Telegram                    │
└─────────────────────────┬───────────────────────────────┘
                          │ Research Directive
┌─────────────────────────▼───────────────────────────────┐
│              🎓 Lab Director                            │
│         Triage: Casual→Reply / Directive→Task           │
└─────────────────────────┬───────────────────────────────┘
                          │ Forward Directive
┌─────────────────────────▼───────────────────────────────┐
│           📋 Planning Office                            │
│      Receive → Plan → Decompose → Submit for Review     │
└─────────────────────────┬───────────────────────────────┘
                          │ Submit Plan
┌─────────────────────────▼───────────────────────────────┐
│           🔍 Review Board                               │
│        Review → Approve ✅ / Veto 🚫 (with feedback)    │
└─────────────────────────┬───────────────────────────────┘
                          │ Approved Plan
┌─────────────────────────▼───────────────────────────────┐
│          📮 Operations Office                           │
│     Assign → Coordinate → Monitor → Consolidate → Report│
└───┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────┘
    │      │      │      │      │      │      │      │
┌───▼──┐┌──▼───┐┌─▼────┐┌─▼────┐┌─▼────┐┌─▼────┐┌─▼────┐┌─▼────┐
│PI-CS ││PI-Chem││PI-Bio││PI-Mat││PI-Med││PI-Agr││PI-Env││PI-Eng│
└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘
```

### Coordination Roles (4)

| Role | Responsibility | Key Function |
|------|----------------|--------------|
| 🎓 **Lab Director** | Message triage, task creation | Receives all directives from PI-Principal, triages casual vs. formal, forwards to Planning Office |
| 📋 **Planning Office** | Research strategy, task decomposition | Designs comprehensive plans, breaks down into sub-tasks with deliverables |
| 🔍 **Review Board** | Quality gate, approval/veto | Reviews plans for completeness and feasibility, can veto with feedback |
| 📮 **Operations Office** | Task assignment, coordination | Assigns to PIs, monitors progress, consolidates results, reports back |

### Discipline PIs (8)

| Discipline | Agent ID | Expertise |
|------------|----------|-----------|
| 🖥️ Computer Science | `pi_cs` | AI/ML, Software Engineering, Data Systems, Algorithms |
| 🧪 Chemistry | `pi_chem` | Organic, Inorganic, Analytical, Computational Chemistry |
| 🧬 Biology | `pi_bio` | Molecular Biology, Genetics, Bioinformatics, Systems Biology |
| 🔩 Materials Science | `pi_mat` | Nanomaterials, Polymers, Composites, Characterization |
| 🏥 Medicine | `pi_med` | Drug Discovery, Clinical Research, Medical Imaging, Pharmacology |
| 🌾 Agriculture | `pi_agr` | Crop Science, Precision Agriculture, Food Security, Plant Protection |
| 🌍 Environmental Science | `pi_env` | Climate, Ecology, Pollution, Sustainability, Conservation |
| ⚙️ Engineering | `pi_eng` | Mechanical, Electrical, Chemical, Civil Engineering, Automation |

---

## 🔐 Permission Matrix

**Not "send whenever you want" — real checks and balances.**

| From ↓ → To | Lab Director | Planning | Review | Operations | PIs |
|-------------|--------------|----------|--------|------------|-----|
| **PI-Principal** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Lab Director** | — | ✅ | ❌ | ❌ | ❌ |
| **Planning Office** | ❌ | — | ✅ | ❌ | ❌ |
| **Review Board** | ❌ | ✅ (Veto) | — | ✅ (Approve) | ❌ |
| **Operations Office** | ✅ (Report) | ❌ | ❌ | — | ✅ |
| **PIs** | ❌ | ❌ | ❌ | ✅ (Progress) | ❌ |

### Key Rules

1. **PI-Principal → Lab Director only**: All directives flow through Lab Director
2. **Single-direction flow**: Lab Director → Planning → Review → Operations → PIs
3. **Veto power**: Review Board can veto Planning Office (must provide feedback)
4. **No cross-PI communication**: PIs coordinate only through Operations Office
5. **Report channel**: Only Operations Office reports final results to Lab Director

See [`protocols/permissions.md`](protocols/permissions.md) for complete rules.

---

## 📦 Installation

### Prerequisites

- **OpenClaw** installed: `brew install openclaw` or download from https://openclaw.ai
- **Python 3.9+**: `python3 --version`
- **Git**: `git --version`

### Step-by-Step

```bash
# 1. Clone repository
git clone https://github.com/onepersonlab/onepersonlab-agents.git
cd onepersonlab-agents

# 2. Run installer (automatically registers 12 agents)
chmod +x install.sh && ./install.sh

# 3. Start data refresh loop (background)
bash scripts/run_loop.sh &

# 4. Start dashboard server
python3 dashboard/server.py

# 5. Open browser
open http://127.0.0.1:7891
```

### What `install.sh` Does

- ✅ Creates 12 Agent Workspaces (`~/.openclaw/workspace-*`)
- ✅ Writes SOUL.md personality files for each role
- ✅ Registers agents with permission matrix to `openclaw.json`
- ✅ Initializes data directory with demo task
- ✅ Runs first data sync
- ✅ Restarts OpenClaw Gateway

---

## 📝 Usage

### Via Messaging (Feishu/Telegram/Signal)

1. **Configure channel** in OpenClaw, set Lab Director as entry point
2. **Send research directive**:
   ```
   I want to discover new drug candidates for Alzheimer's disease.
   Focus on: target identification, compound screening, and ADME-Tox prediction.
   ```
3. **Lab Director triages** and creates task `SLC-YYYYMMDD-NNN`
4. **Watch progress** on dashboard: http://127.0.0.1:7891
5. **Receive final report** via same messaging channel

### Via Dashboard

1. **Open dashboard**: http://127.0.0.1:7891
2. **View active directives** in Research Dashboard tab
3. **Monitor progress** by department in Dept Coordination tab
4. **Review completed** tasks in Archive tab
5. **Configure models** per agent in Models tab

### Task Lifecycle

```
[Inbox] → [Lab Director Triage] → [Planning] → [Review] → [Assigned] → [In Progress] → [Completed]
                                    ↑                                        │
                                    └────────── Veto ────────────────────────┘
```

### Kanban Commands

```bash
# Create task
python3 scripts/kanban_update.py create SLC-20260318-001 "Research goal" State Org Official

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

## 💡 Examples

### Example 1: Drug Discovery

**Directive:**
```
I want to discover new drug candidates for Alzheimer's disease.
Requirements:
1. Target identification and validation
2. Compound library screening
3. ML-based ADME-Tox prediction
4. In vitro validation plan
```

**Flow:**
1. Lab Director → Creates `SLC-20260318-001`
2. Planning Office → 4 sub-tasks (Med, Chem, CS, Bio)
3. Review Board → Approves ✅
4. Operations Office → Assigns to 4 PIs
5. Final Report → Integrated findings with recommendations

### Example 2: Climate Impact Assessment

**Directive:**
```
Assess climate change impact on crop yields in Southeast Asia.
Include: temperature trends, precipitation patterns, adaptation strategies.
```

**Involved PIs:** `pi_env`, `pi_agr`, `pi_cs` (data analysis)

### Example 3: Materials Design

**Directive:**
```
Design novel polymer composite for flexible electronics.
Requirements: high conductivity, mechanical flexibility, biocompatibility.
```

**Involved PIs:** `pi_mat`, `pi_chem`, `pi_eng`

See [`examples/`](examples/) for more detailed case studies.

---

## 📊 Comparison

| Feature | CrewAI | AutoGen | MetaGPT | **SciLab-Agents** |
|---------|--------|---------|---------|-------------------|
| **Review Mechanism** | ❌ None | ⚠️ Optional | ⚠️ Human-in-loop | ✅ Review Board with veto |
| **Real-time Dashboard** | ❌ | ❌ | ❌ | ✅ Kanban + Timeline |
| **Task Intervention** | ❌ | ❌ | ❌ | ✅ Stop/Cancel/Resume |
| **Permission Control** | ❌ | ❌ | ❌ | ✅ Strict matrix |
| **Message Triage** | ❌ | ❌ | ❌ | ✅ Lab Director filters |
| **Audit Trail** | ⚠️ Partial | ❌ | ⚠️ Partial | ✅ Complete flow log |
| **Model Hot-swap** | ❌ | ❌ | ❌ | ✅ Per-agent config |
| **Deployment** | Medium | High | Medium | **One-click** |

**Core advantage: Institutional oversight + Full observability + Real-time intervention**

---

## 📁 Project Structure

```
onepersonlab-agents/
├── agents/                     # 12 Agent SOUL.md definitions
│   ├── lab_director/           # Triage & coordination
│   ├── planning_office/        # Strategy & planning
│   ├── review_board/           # Quality gate
│   ├── operations_office/      # Task coordination
│   └── pi_*/                   # 8 Discipline PIs
├── dashboard/                  # Real-time Kanban
│   ├── dashboard.html          # Frontend UI
│   └── server.py               # API server
├── scripts/                    # Automation scripts
│   ├── kanban_update.py        # Kanban CLI
│   ├── run_loop.sh             # Data refresh loop
│   ├── sync_*.py               # Data synchronization
│   └── ...
├── protocols/                  # Process documentation
│   └── permissions.md          # Permission matrix
├── docs/                       # Documentation
│   ├── getting-started.md      # Setup guide
│   └── screenshots/            # UI screenshots
├── examples/                   # Usage examples
│   ├── drug-discovery.md       # Drug discovery case
│   ├── climate-assessment.md   # Climate case
│   └── ...
├── docker/                     # Docker configuration
│   ├── Dockerfile
│   └── demo_data/
├── tests/                      # End-to-end tests
├── install.sh                  # One-click installer
├── docker-compose.yml          # Docker Compose config
├── README.md                   # This file
└── LICENSE                     # MIT License
```

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas We Need Help

- 🎨 **UI/UX**: Dark/light theme, responsive design, animations
- 🤖 **New PIs**: Physics, Mathematics, Neuroscience, etc.
- 📦 **Skills**: Domain-specific skills for each PI
- 🔗 **Integrations**: Notion, Jira, GitHub, Electronic Lab Notebooks
- 🌐 **i18n**: Translations (Chinese, Japanese, Korean, Spanish)
- 📱 **Mobile**: PWA, mobile responsiveness
- 📊 **Analytics**: Agent performance metrics, cost tracking

### Development Setup

```bash
# Fork and clone
git clone https://github.com/onepersonlab/onepersonlab-agents.git
cd onepersonlab-agents

# Install dependencies (if any)
pip install -r requirements.txt  # Coming soon

# Run tests
python3 -m pytest tests/

# Start development server
python3 dashboard/server.py
```

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Inspired by the ancient Chinese "Three Departments and Six Ministries" (三省六部制) governance system (618-907 AD)
- Built on [OpenClaw](https://openclaw.ai) multi-agent framework
- Original concept from [edict-20260301](https://github.com/ingeniousfrog/edict-20260301)

---

## 🔗 Links

- **Documentation**: https://docs.openclaw.ai
- **Community**: https://discord.gg/clawd
- **Skill Hub**: https://clawhub.com
- **Issue Tracker**: https://github.com/onepersonlab/onepersonlab-agents/issues

---

> 🧪 **Governing research with the wisdom of ancient empires**
> 
> *以古制御新技，以智慧驾驭 AI*
> 
> © 2026 OnePersonLab. All rights reserved.
