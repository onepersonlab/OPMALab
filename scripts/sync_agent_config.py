#!/usr/bin/env python3
"""
Synchronize agent configuration from openclaw.json → data/agent_config.json
Supports auto-discovery of skills in agent workspace directories

OPMALab Version: Supports 12 agents (4 Coordination Roles + 8 Discipline PIs)
"""
import json, pathlib, datetime, logging
from file_lock import atomic_json_write

log = logging.getLogger('sync_agent_config')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

# Auto-detect project root (parent of scripts/)
BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
OPENCLAW_CFG = pathlib.Path.home() / '.openclaw' / 'openclaw.json'

# ═══════════════════════════════════════════════════════════════
# OPMALab · 12 Agent Configuration
# 4 Coordination Roles + 8 Discipline PIs
# ═══════════════════════════════════════════════════════════════
ID_LABEL = {
    # Coordination Roles (4)
    'lab_director':    {'label': 'Lab Director',    'role': 'Lab Director',    'duty': 'Message triage and task creation',                   'emoji': '🎓'},
    'planning_office': {'label': 'Planning Office', 'role': 'Planning Director', 'duty': 'Research strategy and task decomposition',           'emoji': '📋'},
    'review_board':    {'label': 'Review Board',    'role': 'Review Chair',      'duty': 'Quality review and veto mechanism',                  'emoji': '🔍'},
    'operations_office': {'label': 'Operations Office', 'role': 'Operations Director', 'duty': 'Task assignment and coordination reporting',   'emoji': '📮'},
    
    # Discipline PIs (8)
    'pi_cs':   {'label': 'PI-CS',   'role': 'Computer Science PI', 'duty': 'AI/ML, Software Engineering, Data Systems',       'emoji': '🖥️'},
    'pi_chem': {'label': 'PI-Chem', 'role': 'Chemistry PI',        'duty': 'Organic, Inorganic, Analytical, Computational Chemistry', 'emoji': '🧪'},
    'pi_bio':  {'label': 'PI-Bio',  'role': 'Biology PI',          'duty': 'Molecular Biology, Genetics, Bioinformatics',     'emoji': '🧬'},
    'pi_mat':  {'label': 'PI-Mat',  'role': 'Materials Science PI','duty': 'Nanomaterials, Polymers, Composites',             'emoji': '🔩'},
    'pi_med':  {'label': 'PI-Med',  'role': 'Medicine PI',         'duty': 'Drug Discovery, Clinical Research, Medical Imaging', 'emoji': '🏥'},
    'pi_agr':  {'label': 'PI-Agr',  'role': 'Agriculture PI',      'duty': 'Crop Science, Precision Agriculture, Food Security', 'emoji': '🌾'},
    'pi_env':  {'label': 'PI-Env',  'role': 'Environmental Science PI', 'duty': 'Climate, Ecology, Pollution, Sustainability', 'emoji': '🌍'},
    'pi_eng':  {'label': 'PI-Eng',  'role': 'Engineering PI',      'duty': 'Mechanical, Electrical, Chemical, Civil Engineering', 'emoji': '⚙️'},
}

KNOWN_MODELS = [
    {'id': 'anthropic/claude-sonnet-4-6', 'label': 'Claude Sonnet 4.6', 'provider': 'Anthropic'},
    {'id': 'anthropic/claude-opus-4-5',   'label': 'Claude Opus 4.5',   'provider': 'Anthropic'},
    {'id': 'anthropic/claude-haiku-3-5',  'label': 'Claude Haiku 3.5',  'provider': 'Anthropic'},
    {'id': 'openai/gpt-4o',               'label': 'GPT-4o',            'provider': 'OpenAI'},
    {'id': 'openai/gpt-4o-mini',          'label': 'GPT-4o Mini',       'provider': 'OpenAI'},
    {'id': 'openai-codex/gpt-5.3-codex',  'label': 'GPT-5.3 Codex',     'provider': 'OpenAI Codex'},
    {'id': 'google/gemini-2.0-flash',     'label': 'Gemini 2.0 Flash',  'provider': 'Google'},
    {'id': 'google/gemini-2.5-pro',       'label': 'Gemini 2.5 Pro',    'provider': 'Google'},
    {'id': 'copilot/claude-sonnet-4',     'label': 'Claude Sonnet 4',   'provider': 'Copilot'},
    {'id': 'copilot/claude-opus-4.5',     'label': 'Claude Opus 4.5',   'provider': 'Copilot'},
    {'id': 'github-copilot/claude-opus-4.6', 'label': 'Claude Opus 4.6', 'provider': 'GitHub Copilot'},
    {'id': 'copilot/gpt-4o',              'label': 'GPT-4o',            'provider': 'Copilot'},
    {'id': 'copilot/gemini-2.5-pro',      'label': 'Gemini 2.5 Pro',    'provider': 'Copilot'},
    {'id': 'copilot/o3-mini',             'label': 'o3-mini',           'provider': 'Copilot'},
]


def normalize_model(model_value, fallback='unknown'):
    if isinstance(model_value, str) and model_value:
        return model_value
    if isinstance(model_value, dict):
        return model_value.get('primary') or model_value.get('id') or fallback
    return fallback


def get_skills(workspace: str):
    skills_dir = pathlib.Path(workspace) / 'skills'
    skills = []
    try:
        if skills_dir.exists():
            for d in sorted(skills_dir.iterdir()):
                if d.is_dir():
                    md = d / 'SKILL.md'
                    desc = ''
                    if md.exists():
                        try:
                            for line in md.read_text(encoding='utf-8', errors='ignore').splitlines():
                                line = line.strip()
                                if line and not line.startswith('#') and not line.startswith('---'):
                                    desc = line[:100]
                                    break
                        except Exception:
                            desc = '(read failed)'
                    skills.append({'name': d.name, 'path': str(md), 'exists': md.exists(), 'description': desc})
    except PermissionError as e:
        log.warning(f'Skills directory access denied: {e}')
    return skills


def main():
    cfg = {}
    try:
        cfg = json.loads(OPENCLAW_CFG.read_text())
    except Exception as e:
        log.warning(f'cannot read openclaw.json: {e}')
        return

    agents_cfg = cfg.get('agents', {})
    default_model = normalize_model(agents_cfg.get('defaults', {}).get('model', {}), 'unknown')
    agents_list = agents_cfg.get('list', [])

    result = []
    seen_ids = set()
    for ag in agents_list:
        ag_id = ag.get('id', '')
        if ag_id not in ID_LABEL:
            continue
        meta = ID_LABEL[ag_id]
        workspace = ag.get('workspace', str(pathlib.Path.home() / f'.openclaw/workspace-{ag_id}'))
        result.append({
            'id': ag_id,
            'label': meta['label'], 'role': meta['role'], 'duty': meta['duty'], 'emoji': meta['emoji'],
            'model': normalize_model(ag.get('model', default_model), default_model),
            'defaultModel': default_model,
            'workspace': workspace,
            'skills': get_skills(workspace),
            'allowAgents': ag.get('subagents', {}).get('allowAgents', []),
        })
        seen_ids.add(ag_id)

    # OPMALab: No automatic addition of extra agents
    # All agents must be explicitly configured in openclaw.json agents.list
    # This prevents accidental creation of unwanted workspaces

    payload = {
        'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'defaultModel': default_model,
        'knownModels': KNOWN_MODELS,
        'agents': result,
    }
    DATA.mkdir(exist_ok=True)
    atomic_json_write(DATA / 'agent_config.json', payload)
    log.info(f'{len(result)} agents synced')

    # Deploy SOUL.md to workspaces
    deploy_soul_files()
    # Sync scripts/ to workspaces
    sync_scripts_to_workspaces()


# ═══════════════════════════════════════════════════════════════
# OPMALab · SOUL File Deployment Map
# Maps project agents/xxx → workspace-xxx
# ═══════════════════════════════════════════════════════════════
_SOUL_DEPLOY_MAP = {
    'lab_director':    'lab_director',
    'planning_office': 'planning_office',
    'review_board':    'review_board',
    'operations_office': 'operations_office',
    'pi_cs':   'pi_cs',
    'pi_chem': 'pi_chem',
    'pi_bio':  'pi_bio',
    'pi_mat':  'pi_mat',
    'pi_med':  'pi_med',
    'pi_agr':  'pi_agr',
    'pi_env':  'pi_env',
    'pi_eng':  'pi_eng',
}

def sync_scripts_to_workspaces():
    """Sync project scripts/ directory to each OPMALab agent workspace"""
    scripts_src = BASE / 'scripts'
    if not scripts_src.is_dir():
        return
    synced = 0
    for proj_name, runtime_id in _SOUL_DEPLOY_MAP.items():
        ws_scripts = pathlib.Path.home() / f'.openclaw/workspace-{runtime_id}' / 'scripts'
        ws_scripts.mkdir(parents=True, exist_ok=True)
        for src_file in scripts_src.iterdir():
            if src_file.suffix not in ('.py', '.sh') or src_file.stem.startswith('__'):
                continue
            dst_file = ws_scripts / src_file.name
            try:
                src_text = src_file.read_bytes()
            except Exception:
                continue
            try:
                dst_text = dst_file.read_bytes() if dst_file.exists() else b''
            except Exception:
                dst_text = b''
            if src_text != dst_text:
                dst_file.write_bytes(src_text)
                synced += 1
    if synced:
        log.info(f'{synced} script files synced to OPMALab workspaces')


def deploy_soul_files():
    """Deploy project agents/xxx/SOUL.md to ~/.openclaw/workspace-xxx/SOUL.md"""
    agents_dir = BASE / 'agents'
    deployed = 0
    for proj_name, runtime_id in _SOUL_DEPLOY_MAP.items():
        src = agents_dir / proj_name / 'SOUL.md'
        if not src.exists():
            continue
        ws_dst = pathlib.Path.home() / f'.openclaw/workspace-{runtime_id}' / 'SOUL.md'
        ws_dst.parent.mkdir(parents=True, exist_ok=True)
        # Compare content to avoid unnecessary writes
        src_text = src.read_text(encoding='utf-8', errors='ignore')
        try:
            dst_text = ws_dst.read_text(encoding='utf-8', errors='ignore')
        except FileNotFoundError:
            dst_text = ''
        if src_text != dst_text:
            ws_dst.write_text(src_text, encoding='utf-8')
            deployed += 1
        # Create sessions directory for each agent
        sess_dir = pathlib.Path.home() / f'.openclaw/agents/{runtime_id}/sessions'
        sess_dir.mkdir(parents=True, exist_ok=True)
    if deployed:
        log.info(f'{deployed} SOUL.md files deployed to OPMALab workspaces')


if __name__ == '__main__':
    main()
