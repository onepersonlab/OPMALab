# 🚀 Getting Started with SciLab-Agents

> From zero to running in 5 minutes

---

## Prerequisites

Before installing SciLab-Agents, ensure you have:

- **OpenClaw** installed and initialized
- **Python 3.9+** available
- **Git** for cloning the repository

---

## Step 1: Install OpenClaw

SciLab-Agents runs on [OpenClaw](https://openclaw.ai). Install it first:

```bash
# macOS
brew install openclaw

# Or download from
# https://openclaw.ai/download
```

Initialize OpenClaw:

```bash
openclaw init
```

Follow the prompts to configure your API keys and preferences.

---

## Step 2: Clone and Install SciLab-Agents

```bash
# Clone repository
git clone https://github.com/onepersonlab/onepersonlab-agents.git
cd onepersonlab-agents

# Run installer
chmod +x install.sh && ./install.sh
```

The installer automatically:
- ✅ Creates 12 Agent Workspaces (`~/.openclaw/workspace-*`)
- ✅ Writes SOUL.md personality files for each role
- ✅ Registers agents with permission matrix to `openclaw.json`
- ✅ Initializes data directory with demo task
- ✅ Runs first data sync
- ✅ Restarts Gateway

---

## Step 3: Configure Messaging Channel

Configure your preferred messaging channel (Feishu / Telegram / Signal) in OpenClaw:

```bash
# List current channels
openclaw channels list

# Add Feishu channel (Lab Director as entry point)
openclaw channels add feishu --agent lab_director
```

The Lab Director agent will be your primary contact for all research directives.

---

## Step 4: Start Services

### Start Data Refresh Loop (Background)

```bash
bash scripts/run_loop.sh &
```

This keeps the dashboard synchronized with OpenClaw runtime data every 15 seconds.

### Start Dashboard Server

```bash
python3 dashboard/server.py
```

### Open Dashboard

```bash
open http://127.0.0.1:7891
```

You should see the SciLab Dashboard with:
- **Research Dashboard**: Active directives by status
- **Dept Coordination**: Current workload by department
- **Team Overview**: Agent performance metrics
- **Archive**: Completed directives

---

## Step 5: Send Your First Directive

### Via Messaging

Send a message to Lab Director via your configured channel:

```
I want to build an AI platform for drug candidate discovery.
I need expertise in chemistry, biology, and machine learning.
Timeline: 2 weeks
```

### What Happens Next

1. **Lab Director** receives message → Triage (casual vs. directive)
2. **Creates task** `SLC-YYYYMMDD-001` with summarized title
3. **Forwards to Planning Office** for detailed planning
4. **Planning Office** decomposes into sub-tasks:
   - T01 (pi_chem): Compound library design
   - T02 (pi_bio): Target validation plan
   - T03 (pi_cs): ML model architecture
5. **Review Board** reviews plan → Approves ✅
6. **Operations Office** assigns to PIs → Monitors progress
7. **PIs execute** → Report deliverables
8. **Operations Office** consolidates → Reports to Lab Director
9. **Lab Director** replies to you with final results

### Track Progress

Watch the dashboard for real-time updates:
- Task moves through states: Inbox → Planning → Review → Assigned → In Progress → Completed
- Each department's workload visible in Dept Coordination tab
- Full flow log in task detail view

---

## Step 6: Explore Dashboard Features

### Research Dashboard (📋)

- View all active directives by status
- Filter by department
- Click any directive for detail view
- Stop/Cancel/Resume actions available

### Dept Coordination (🔭)

- See current workload per department
- Agent health status (🟢 Active 🟡 Stalled 🔴 Alert)
- Model configuration per agent

### Team Overview (👥)

- Token consumption by agent
- Completed tasks count
- Activity timeline

### Archive (📚)

- Completed directives with full flow logs
- Five-stage timeline: Directive → Planning → Review → Execution → Report
- Export as Markdown

### Models (⚙️)

- Configure LLM per agent
- Hot-swap without restart
- Change log visible

### Skills (🛠️)

- View installed skills per agent
- Add new skills from ClawHub

---

## 🐳 Docker Deployment (Optional)

For isolated demo environment:

```bash
# Build image
docker build -t onepersonlab/scilab-agents:latest .

# Run container
docker run -p 7891:7891 onepersonlab/scilab-agents:latest

# Or use Docker Compose
docker compose up
```

Access dashboard at http://localhost:7891

> Note: Docker demo uses pre-seeded data. For full OpenClaw integration, use native installation.

---

## ⚠️ Troubleshooting

### Gateway Not Starting

```bash
# Check status
openclaw gateway status

# Manual restart
openclaw gateway restart
```

### Agents Not Showing

```bash
# Verify registration
cat ~/.openclaw/openclaw.json | jq '.agents.list[] | .id'

# Re-run installer
./install.sh
```

### Dashboard Not Loading

```bash
# Check server logs
# Look for errors in terminal where server.py is running

# Verify port not in use
lsof -i :7891

# Restart server
python3 dashboard/server.py
```

### Data Not Syncing

```bash
# Check run_loop.sh is running
ps aux | grep run_loop.sh

# Manual sync
python3 scripts/sync_from_openclaw_runtime.py
python3 scripts/sync_agent_config.py
```

---

## 📚 Next Steps

- **Read [protocols/permissions.md](protocols/permissions.md)** for communication rules
- **Explore [examples/](examples/)** for real use cases
- **Join [Discord](https://discord.gg/clawd)** for community support
- **Check [ClawHub](https://clawhub.com)** for new skills

---

## 🆘 Getting Help

- **Documentation**: https://docs.openclaw.ai
- **Issues**: https://github.com/onepersonlab/onepersonlab-agents/issues
- **Discord**: https://discord.gg/clawd

---

> 🧪 Welcome to SciLab-Agents — where ancient wisdom meets modern research!
