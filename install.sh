#!/bin/bash
# ══════════════════════════════════════════════════════════════
# OnePersonLab-Agents · OnePersonLab Multi-Agent Platform
# One-Click Installation Script
# ══════════════════════════════════════════════════════════════
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OC_HOME="$HOME/.openclaw"
OC_CFG="$OC_HOME/openclaw.json"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

banner() {
  echo ""
  echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║  🧪  OnePersonLab-Agents · OnePersonLab           ║${NC}"
  echo -e "${BLUE}║       Multi-Agent Platform                      ║${NC}"
  echo -e "${BLUE}║       Installation Wizard                       ║${NC}"
  echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
  echo ""
}

log()   { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
info()  { echo -e "${BLUE}ℹ️  $1${NC}"; }

# ── Step 0: Dependencies Check ───────────────────────────────
check_deps() {
  info "Checking dependencies..."
  
  if ! command -v openclaw &>/dev/null; then
    error "OpenClaw CLI not found. Install: https://openclaw.ai"
    exit 1
  fi
  log "OpenClaw CLI: $(openclaw --version 2>/dev/null || echo 'OK')"

  if ! command -v python3 &>/dev/null; then
    error "Python3 not found"
    exit 1
  fi
  log "Python3: $(python3 --version)"

  if [ ! -f "$OC_CFG" ]; then
    error "openclaw.json not found. Run 'openclaw' to initialize first."
    exit 1
  fi
  log "openclaw.json: $OC_CFG"
}

# ── Step 1: Create Workspaces ────────────────────────────────
create_workspaces() {
  info "Creating Agent Workspaces..."
  
  # OnePersonLab-Agents: 12 roles (4 coordination + 8 discipline PIs)
  AGENTS=(
    lab_director
    planning_office
    review_board
    operations_office
    pi_cs
    pi_chem
    pi_bio
    pi_mat
    pi_med
    pi_agr
    pi_env
    pi_eng
  )
  
  for agent in "${AGENTS[@]}"; do
    ws="$OC_HOME/workspace-$agent"
    mkdir -p "$ws/skills"
    if [ -f "$REPO_DIR/agents/$agent/SOUL.md" ]; then
      sed "s|__REPO_DIR__|$REPO_DIR|g" "$REPO_DIR/agents/$agent/SOUL.md" > "$ws/SOUL.md"
    fi
    log "Workspace created: $ws"
  done

  # Common AGENTS.md (work protocol)
  for agent in "${AGENTS[@]}"; do
    cat > "$OC_HOME/workspace-$agent/AGENTS.md" << 'AGENTS_EOF'
# AGENTS.md · Work Protocol

1. Reply "Task received" when assigned.
2. Output must include: Task ID, Result, Evidence/Paths, Blockers.
3. For collaboration, coordinate through Operations Office.
4. Destructive/external actions require explicit approval.
AGENTS_EOF
  done
}

# ── Step 2: Register Agents ──────────────────────────────────
register_agents() {
  info "Registering OnePersonLab-Agents..."

  # Backup config
  cp "$OC_CFG" "$OC_CFG.bak.opmalab-$(date +%Y%m%d-%H%M%S)"
  log "Config backed up: $OC_CFG.bak.*"

  python3 << 'PYEOF'
import json, pathlib, sys

cfg_path = pathlib.Path.home() / '.openclaw' / 'openclaw.json'
cfg = json.loads(cfg_path.read_text())

# OnePersonLab-Agents: 12 roles with permission matrix
# Based on protocols/permissions.md
OPMALAB_AGENTS = [
    # Coordination Roles (4)
    {"id": "lab_director",    "subagents": {"allowAgents": ["planning_office"]}},
    {"id": "planning_office", "subagents": {"allowAgents": ["review_board"]}},
    {"id": "review_board",    "subagents": {"allowAgents": ["operations_office", "planning_office"]}},
    {"id": "operations_office", "subagents": {"allowAgents": [
        "pi_cs", "pi_chem", "pi_bio", "pi_mat", 
        "pi_med", "pi_agr", "pi_env", "pi_eng"
    ]}},
    
    # Discipline PIs (8)
    {"id": "pi_cs",      "subagents": {"allowAgents": ["operations_office"]}},
    {"id": "pi_chem",    "subagents": {"allowAgents": ["operations_office"]}},
    {"id": "pi_bio",     "subagents": {"allowAgents": ["operations_office"]}},
    {"id": "pi_mat",     "subagents": {"allowAgents": ["operations_office"]}},
    {"id": "pi_med",     "subagents": {"allowAgents": ["operations_office"]}},
    {"id": "pi_agr",     "subagents": {"allowAgents": ["operations_office"]}},
    {"id": "pi_env",     "subagents": {"allowAgents": ["operations_office"]}},
    {"id": "pi_eng",     "subagents": {"allowAgents": ["operations_office"]}},
]

# Get existing agents configuration
agents_cfg = cfg.setdefault('agents', {})
existing_agents = agents_cfg.get('list', [])

# OPMALab agent IDs
opmalab_ids = {ag['id'] for ag in OPMALAB_AGENTS}

# Keep existing agents that are NOT OPMALab agents (preserve other projects)
# But remove any old OPMALab agents to avoid duplicates
preserved_agents = []
removed_count = 0
for ag in existing_agents:
    ag_id = ag.get('id', '')
    if ag_id in opmalab_ids:
        removed_count += 1
        print(f'  - removed existing OPMALab agent: {ag_id}')
    else:
        preserved_agents.append(ag)
        print(f'  ✓ preserved non-OPMALab agent: {ag_id}')

if removed_count == 0 and len(existing_agents) == 0:
    print('  (no existing agents)')

# Build final agents list: preserved + OPMALab
agents_list = preserved_agents

# Register OPMALab agents
added = 0
for ag in OPMALAB_AGENTS:
    ag_id = ag['id']
    ws = str(pathlib.Path.home() / f'.openclaw/workspace-{ag_id}')
    entry = {'id': ag_id, 'workspace': ws, **{k:v for k,v in ag.items() if k!='id'}}
    agents_list.append(entry)
    added += 1
    print(f'  + registered OPMALab agent: {ag_id}')

print(f'  ✓ {added} OPMALab agents registered')
print(f'  ✓ {len(preserved_agents)} non-OPMALab agents preserved')

agents_cfg['list'] = agents_list
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
print(f'Done: {len(agents_list)} total agents in config')
PYEOF

  log "Agents registered successfully"
}

# ── Step 3: Initialize Data ──────────────────────────────────
init_data() {
  info "Initializing data directory..."
  
  mkdir -p "$REPO_DIR/data"
  
  # Initialize empty files
  for f in live_status.json agent_config.json model_change_log.json; do
    if [ ! -f "$REPO_DIR/data/$f" ]; then
      echo '{}' > "$REPO_DIR/data/$f"
    fi
  done
  echo '[]' > "$REPO_DIR/data/pending_model_changes.json"

  # Initial tasks file with OnePersonLab demo
  if [ ! -f "$REPO_DIR/data/tasks_source.json" ]; then
    python3 << 'PYEOF'
import json, pathlib, os

tasks = [
    {
        "id": "OPL-DEMO-001",
        "title": "🎉 OnePersonLab-Agents Initialized",
        "official": "Operations Director",
        "org": "Operations Office",
        "state": "Done",
        "now": "OnePersonLab platform is ready",
        "eta": "-",
        "block": "None",
        "output": "",
        "ac": "All systems operational",
        "flow_log": [
            {"at": "2026-03-18T00:00:00Z", "from": "Human User", "to": "Lab Director", "remark": "Issue directive: Initialize OnePersonLab platform"},
            {"at": "2026-03-18T00:01:00Z", "from": "Lab Director", "to": "Planning Office", "remark": "Forward directive for planning"},
            {"at": "2026-03-18T00:02:00Z", "from": "Planning Office", "to": "Review Board", "remark": "Submit plan for review"},
            {"at": "2026-03-18T00:03:00Z", "from": "Review Board", "to": "Operations Office", "remark": "✅ Plan approved"},
            {"at": "2026-03-18T00:04:00Z", "from": "Operations Office", "to": "Discipline PIs", "remark": "Assign: Platform initialization"},
            {"at": "2026-03-18T00:05:00Z", "from": "Discipline PIs", "to": "Operations Office", "remark": "✅ Complete"},
            {"at": "2026-03-18T00:06:00Z", "from": "Operations Office", "to": "Lab Director", "remark": "✅ Final report submitted"}
        ]
    }
]

data_dir = pathlib.Path(os.environ.get('REPO_DIR', '.')) / 'data'
data_dir.mkdir(exist_ok=True)
(data_dir / 'tasks_source.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2))
print('tasks_source.json initialized')
PYEOF
  fi

  log "Data directory initialized: $REPO_DIR/data"
}

# ── Step 4: First Data Sync ──────────────────────────────────
first_sync() {
  info "Running first data sync..."
  cd "$REPO_DIR"
  
  REPO_DIR="$REPO_DIR" python3 scripts/sync_agent_config.py || warn "sync_agent_config warnings"
  python3 scripts/refresh_live_data.py || warn "refresh_live_data warnings"
  
  log "Initial sync completed"
}

# ── Step 5: Restart Gateway ──────────────────────────────────
restart_gateway() {
  info "Restarting OpenClaw Gateway..."
  if openclaw gateway restart 2>/dev/null; then
    log "Gateway restarted successfully"
  else
    warn "Gateway restart failed. Please run: openclaw gateway restart"
  fi
}

# ── Main ─────────────────────────────────────────────────────
banner
check_deps
create_workspaces
register_agents
init_data
first_sync
restart_gateway

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🎉  OnePersonLab-Agents Installation Complete!        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next Steps:"
echo "  1. Start data refresh:  bash scripts/run_loop.sh &"
echo "  2. Start dashboard:     python3 dashboard/server.py"
echo "  3. Open dashboard:      http://127.0.0.1:9731"
echo ""
info "Documentation: README.md"
echo ""
echo "🧪 OnePersonLab-Agents: Governing research with institutional oversight"
echo "   https://github.com/onepersonlab/OPMALab"
