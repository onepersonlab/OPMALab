#!/usr/bin/env python3
"""
OPMALab · Kanban Local API Server
Port: 9731 (modify via --port)

Endpoints:
  GET  /                       → dashboard.html
  GET  /api/live-status        → data/live_status.json
  GET  /api/agent-config       → data/agent_config.json
  POST /api/set-model          → {agentId, model}
  GET  /api/model-change-log   → data/model_change_log.json
  GET  /api/last-result        → data/last_model_change_result.json
"""
import json, pathlib, subprocess, sys, threading, argparse, datetime, logging, re, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Import file lock for safe concurrent access
scripts_dir = str(pathlib.Path(__file__).parent.parent / 'scripts')
sys.path.insert(0, scripts_dir)
from file_lock import atomic_json_read, atomic_json_write, atomic_json_update
from utils import validate_url

log = logging.getLogger('server')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

OCLAW_HOME = pathlib.Path.home() / '.openclaw'
MAX_REQUEST_BODY = 1 * 1024 * 1024  # 1 MB
ALLOWED_ORIGIN = None  # Set via --cors; None means restrict to localhost
_DEFAULT_ORIGINS = {'http://127.0.0.1:9731', 'http://localhost:9731'}
_SAFE_NAME_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')

BASE = pathlib.Path(__file__).parent
DATA = BASE.parent / "data"
SCRIPTS = BASE.parent / 'scripts'


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default if default is not None else {}


def cors_headers(h):
    req_origin = h.headers.get('Origin', '')
    if ALLOWED_ORIGIN:
        origin = ALLOWED_ORIGIN
    elif req_origin in _DEFAULT_ORIGINS:
        origin = req_origin
    else:
        origin = 'http://127.0.0.1:9731'
    h.send_header('Access-Control-Allow-Origin', origin)
    h.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    h.send_header('Access-Control-Allow-Headers', 'Content-Type')


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def load_tasks():
    return atomic_json_read(DATA / 'tasks_source.json', [])


def save_tasks(tasks):
    atomic_json_write(DATA / 'tasks_source.json', tasks)
    # Trigger refresh asynchronously
    def _refresh():
        try:
            subprocess.run(['python3', str(SCRIPTS / 'refresh_live_data.py')], timeout=30)
        except Exception as e:
            log.warning(f'refresh_live_data.py trigger failed: {e}')
    threading.Thread(target=_refresh, daemon=True).start()


def handle_task_action(task_id, action, reason):
    """Stop/cancel/resume a task from the dashboard."""
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}

    old_state = task.get('state', '')

    if action == 'stop':
        task['state'] = 'Blocked'
        task['block'] = reason or 'Stopped by user'
        task['now'] = f'⏸️ Stopped: {reason}'
    elif action == 'cancel':
        task['state'] = 'Cancelled'
        task['block'] = reason or 'Cancelled by user'
        task['now'] = f'🚫 Cancelled: {reason}'
    elif action == 'resume':
        task['state'] = task.get('_prev_state', 'Doing')
        task['block'] = 'None'
        task['now'] = f'▶️ Resumed'

    if action in ('stop', 'cancel'):
        task['_prev_state'] = old_state

    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': 'Human User',
        'to': task.get('org', ''),
        'remark': f'{"⏸️ Stop" if action == "stop" else "🚫 Cancel" if action == "cancel" else "▶️ Resume"}: {reason}'
    })
    task['updatedAt'] = now_iso()

    save_tasks(tasks)
    label = {'stop': 'stopped', 'cancel': 'cancelled', 'resume': 'resumed'}[action]
    return {'ok': True, 'message': f'{task_id} {label}'}


def handle_archive_task(task_id, archived, archive_all_done=False):
    """Archive or unarchive a task, or batch-archive all Done/Cancelled tasks."""
    tasks = load_tasks()
    if archive_all_done:
        count = 0
        for t in tasks:
            if t.get('state') in ('Done', 'Cancelled') and not t.get('archived'):
                t['archived'] = True
                t['archivedAt'] = now_iso()
                count += 1
        save_tasks(tasks)
        return {'ok': True, 'message': f'{count} tasks archived', 'count': count}
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    task['archived'] = archived
    if archived:
        task['archivedAt'] = now_iso()
    else:
        task.pop('archivedAt', None)
    task['updatedAt'] = now_iso()
    save_tasks(tasks)
    label = 'archived' if archived else 'unarchived'
    return {'ok': True, 'message': f'{task_id} {label}'}


def update_task_todos(task_id, todos):
    """Update the todos list for a task."""
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}

    task['todos'] = todos
    task['updatedAt'] = now_iso()
    save_tasks(tasks)
    return {'ok': True, 'message': f'{task_id} todos updated'}


def read_skill_content(agent_id, skill_name):
    """Read SKILL.md content for a specific skill."""
    if not _SAFE_NAME_RE.match(agent_id) or not _SAFE_NAME_RE.match(skill_name):
        return {'ok': False, 'error': 'Invalid characters in parameters'}
    cfg = read_json(DATA / 'agent_config.json', {})
    agents = cfg.get('agents', [])
    ag = next((a for a in agents if a.get('id') == agent_id), None)
    if not ag:
        return {'ok': False, 'error': f'Agent {agent_id} not found'}
    sk = next((s for s in ag.get('skills', []) if s.get('name') == skill_name), None)
    if not sk:
        return {'ok': False, 'error': f'Skill {skill_name} not found'}
    skill_path = pathlib.Path(sk.get('path', '')).resolve()
    allowed_roots = (OCLAW_HOME.resolve(), BASE.parent.resolve())
    if not any(str(skill_path).startswith(str(root)) for root in allowed_roots):
        return {'ok': False, 'error': 'Path outside allowed directories'}
    if not skill_path.exists():
        return {'ok': True, 'name': skill_name, 'agent': agent_id, 'content': '(SKILL.md not found)', 'path': str(skill_path)}
    try:
        content = skill_path.read_text()
        return {'ok': True, 'name': skill_name, 'agent': agent_id, 'content': content, 'path': str(skill_path)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def add_skill_to_agent(agent_id, skill_name, description, trigger=''):
    """Create a new skill for an agent with a standardized SKILL.md template."""
    if not _SAFE_NAME_RE.match(skill_name):
        return {'ok': False, 'error': f'Invalid skill_name: {skill_name}'}
    if not _SAFE_NAME_RE.match(agent_id):
        return {'ok': False, 'error': f'Invalid agentId: {agent_id}'}
    workspace = OCLAW_HOME / f'workspace-{agent_id}' / 'skills' / skill_name
    workspace.mkdir(parents=True, exist_ok=True)
    skill_md = workspace / 'SKILL.md'
    desc_line = description or skill_name
    trigger_section = f'\n## Trigger Conditions\n{trigger}\n' if trigger else ''
    template = (f'---\n'
                f'name: {skill_name}\n'
                f'description: {desc_line}\n'
                f'---\n\n'
                f'# {skill_name}\n\n'
                f'{desc_line}\n'
                f'{trigger_section}\n'
                f'## Input\n\n'
                f'<!-- Describe what input this skill accepts -->\n\n'
                f'## Processing\n\n'
                f'1. Step one\n'
                f'2. Step two\n\n'
                f'## Output\n\n'
                f'<!-- Describe output format and delivery requirements -->\n\n'
                f'## Notes\n\n'
                f'- (Add constraints, limitations, or special rules here)\n')
    skill_md.write_text(template)
    try:
        subprocess.run(['python3', str(SCRIPTS / 'sync_agent_config.py')], timeout=10)
    except Exception:
        pass
    return {'ok': True, 'message': f'Skill {skill_name} added to {agent_id}', 'path': str(skill_md)}


# ═══════════════════════════════════════════════════════════════
# OPMALab · 12 Agent Configuration
# 4 Coordination Roles + 8 Discipline PIs
# ═══════════════════════════════════════════════════════════════
_AGENT_DEPTS = [
    # Coordination Roles (4)
    {'id': 'lab_director',    'label': 'Lab Director',    'emoji': '🎓', 'role': 'Lab Director',    'rank': 'Coordination'},
    {'id': 'planning_office', 'label': 'Planning Office', 'emoji': '📋', 'role': 'Planning Director', 'rank': 'Coordination'},
    {'id': 'review_board',    'label': 'Review Board',    'emoji': '🔍', 'role': 'Review Chair',      'rank': 'Coordination'},
    {'id': 'operations_office', 'label': 'Operations Office', 'emoji': '📮', 'role': 'Operations Director', 'rank': 'Coordination'},
    
    # Discipline PIs (8)
    {'id': 'pi_cs',   'label': 'PI-CS',   'emoji': '🖥️', 'role': 'Computer Science PI', 'rank': 'Discipline PI'},
    {'id': 'pi_chem', 'label': 'PI-Chem', 'emoji': '🧪', 'role': 'Chemistry PI',        'rank': 'Discipline PI'},
    {'id': 'pi_bio',  'label': 'PI-Bio',  'emoji': '🧬', 'role': 'Biology PI',          'rank': 'Discipline PI'},
    {'id': 'pi_mat',  'label': 'PI-Mat',  'emoji': '🔩', 'role': 'Materials Science PI','rank': 'Discipline PI'},
    {'id': 'pi_med',  'label': 'PI-Med',  'emoji': '🏥', 'role': 'Medicine PI',         'rank': 'Discipline PI'},
    {'id': 'pi_agr',  'label': 'PI-Agr',  'emoji': '🌾', 'role': 'Agriculture PI',      'rank': 'Discipline PI'},
    {'id': 'pi_env',  'label': 'PI-Env',  'emoji': '🌍', 'role': 'Environmental Science PI', 'rank': 'Discipline PI'},
    {'id': 'pi_eng',  'label': 'PI-Eng',  'emoji': '⚙️', 'role': 'Engineering PI',      'rank': 'Discipline PI'},
]

# State to agent mapping for OPMALab
_STATE_AGENT_MAP = {
    'Taizi': 'lab_director',
    'Zhongshu': 'planning_office',
    'Menxia': 'review_board',
    'Assigned': 'operations_office',
    'Review': 'operations_office',
    'Pending': 'planning_office',
}

# Org to agent mapping
_ORG_AGENT_MAP = {
    'Lab Director': 'lab_director',
    'Planning Office': 'planning_office',
    'Review Board': 'review_board',
    'Operations Office': 'operations_office',
    'PI-CS': 'pi_cs', 'PI-Chem': 'pi_chem', 'PI-Bio': 'pi_bio',
    'PI-Mat': 'pi_mat', 'PI-Med': 'pi_med', 'PI-Agr': 'pi_agr',
    'PI-Env': 'pi_env', 'PI-Eng': 'pi_eng',
}


def _check_gateway_alive():
    """Check if Gateway process is running."""
    try:
        result = subprocess.run(['pgrep', '-f', 'openclaw-gateway'],
                                capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _check_gateway_probe():
    """Check if Gateway responds via HTTP probe."""
    try:
        resp = urlopen('http://127.0.0.1:18789/', timeout=3)
        return resp.status == 200
    except Exception:
        return False


def _get_agent_session_status(agent_id):
    """Read agent's sessions.json for activity status."""
    sessions_file = OCLAW_HOME / 'agents' / agent_id / 'sessions' / 'sessions.json'
    if not sessions_file.exists():
        return 0, 0, False
    try:
        data = json.loads(sessions_file.read_text())
        if not isinstance(data, dict):
            return 0, 0, False
        session_count = len(data)
        last_ts = 0
        for v in data.values():
            ts = v.get('updatedAt', 0)
            if isinstance(ts, (int, float)) and ts > last_ts:
                last_ts = ts
        now_ms = int(datetime.datetime.now().timestamp() * 1000)
        age_ms = now_ms - last_ts if last_ts else 9999999999
        is_busy = age_ms <= 2 * 60 * 1000  # Active within 2 minutes
        return last_ts, session_count, is_busy
    except Exception:
        return 0, 0, False


def _check_agent_process(agent_id):
    """Check if openclaw-agent process is running for this agent."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', f'openclaw.*--agent.*{agent_id}'],
            capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _check_agent_workspace(agent_id):
    """Check if agent workspace exists."""
    ws = OCLAW_HOME / f'workspace-{agent_id}'
    return ws.is_dir()


def get_agents_status():
    """Get status of all OPMALab agents."""
    gateway_alive = _check_gateway_alive()
    gateway_probe = _check_gateway_probe() if gateway_alive else False

    agents = []
    seen_ids = set()
    for dept in _AGENT_DEPTS:
        aid = dept['id']
        if aid in seen_ids:
            continue
        seen_ids.add(aid)
        
        has_workspace = _check_agent_workspace(aid)
        last_ts, session_count, is_busy = _get_agent_session_status(aid)
        process_alive = _check_agent_process(aid)
        
        if not has_workspace:
            status = 'unconfigured'
        elif process_alive or is_busy:
            status = 'running'
        elif gateway_alive and gateway_probe:
            status = 'idle'
        else:
            status = 'offline'
        
        agents.append({
            **dept,
            'status': status,
            'lastActive': datetime.datetime.fromtimestamp(last_ts / 1000).strftime('%Y-%m-%d %H:%M') if last_ts else None,
            'sessions': session_count,
            'hasWorkspace': has_workspace,
            'processAlive': process_alive,
        })
    
    return {
        'gateway': {'alive': gateway_alive, 'probe': gateway_probe},
        'agents': agents,
    }


def dispatch_for_state(task_id, task, new_state):
    """Dispatch task to appropriate agent based on state."""
    agent_id = _STATE_AGENT_MAP.get(new_state)
    if not agent_id:
        return
    
    title = task.get('title', 'Task')[:50]
    msg = (
        f'📋 Task {task_id} assigned\n'
        f'Title: {title}\n'
        f'State: {new_state}\n'
        f'Please proceed with your role.'
    )
    
    def _dispatch():
        try:
            if not _check_gateway_alive():
                log.warning(f'⚠️ {task_id} dispatch skipped: Gateway not running')
                return
            cmd = ['openclaw', 'agent', '--agent', agent_id, '-m', msg,
                   '--deliver', '--channel', 'feishu', '--timeout', '300']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=310)
            if result.returncode == 0:
                log.info(f'✅ {task_id} dispatched to {agent_id}')
            else:
                log.warning(f'⚠️ {task_id} dispatch failed: {result.stderr[:200]}')
        except Exception as e:
            log.warning(f'⚠️ {task_id} dispatch error: {e}')
    
    threading.Thread(target=_dispatch, daemon=True).start()


# Minimum title length for directive
_MIN_TITLE_LEN = 10
_JUNK_TITLES = {
    '?', '？', 'ok', 'yes', 'no', 'got it', 'received', 'thanks',
    'test', 'testing', 'hello', 'hi',
}


def handle_create_task(title, org='Planning Office', official='Planning Director', priority='normal', template_id='', params=None, target_dept=''):
    """Create new task from dashboard (directive)."""
    if not title or not title.strip():
        return {'ok': False, 'error': 'Task title cannot be empty'}
    title = title.strip()
    # Strip Conversation info metadata
    title = re.split(r'\n*Conversation info\s*\(', title, maxsplit=1)[0].strip()
    title = re.split(r'\n*```', title, maxsplit=1)[0].strip()
    # Remove directive prefixes
    title = re.sub(r'^(Directive|Order|Task)[\s:：]*', '', title, flags=re.IGNORECASE)
    if len(title) > 100:
        title = title[:100] + '…'
    # Validate title quality
    if len(title) < _MIN_TITLE_LEN:
        return {'ok': False, 'error': f'Title too short ({len(title)}<{_MIN_TITLE_LEN} chars)'}
    if title.lower() in _JUNK_TITLES:
        return {'ok': False, 'error': f'"{title}" is not a valid directive'}
    
    # Generate task ID: OPL-YYYYMMDD-NNN
    today = datetime.datetime.now().strftime('%Y%m%d')
    tasks = load_tasks()
    today_ids = [t['id'] for t in tasks if t.get('id', '').startswith(f'OPL-{today}-')]
    seq = 1
    if today_ids:
        nums = [int(tid.split('-')[-1]) for tid in today_ids if tid.split('-')[-1].isdigit()]
        seq = max(nums) + 1 if nums else 1
    task_id = f'OPL-{today}-{seq:03d}'
    
    # OPMALab flow: Task starts at Planning Office
    initial_org = 'Planning Office'
    new_task = {
        'id': task_id,
        'title': title,
        'official': official,
        'org': initial_org,
        'state': 'Zhongshu',  # Internal state for Planning Office
        'now': 'Waiting for Planning Office',
        'eta': '-',
        'block': 'None',
        'output': '',
        'ac': '',
        'priority': priority,
        'templateId': template_id,
        'templateParams': params or {},
        'flow_log': [{
            'at': now_iso(),
            'from': 'Human User',
            'to': initial_org,
            'remark': f'Directive: {title}'
        }],
        'updatedAt': now_iso(),
    }
    if target_dept:
        new_task['targetDept'] = target_dept
    tasks.insert(0, new_task)
    save_tasks(tasks)
    log.info(f'Created task: {task_id} | {title[:40]}')

    # Dispatch to Lab Director agent asynchronously
    def dispatch_to_agent():
        try:
            if not _check_gateway_alive():
                log.warning(f'⚠️ {task_id} dispatch skipped: Gateway not running')
                return
            msg = (
                f'📋 New Directive (logged in dashboard)\n'
                f'Task ID: {task_id}\n'
                f'Directive: {title}\n'
                f'⚠️ Task already in dashboard, do not create duplicate.\n'
                f'Please forward to Planning Office for planning.'
            )
            cmd = ['openclaw', 'agent', '--agent', 'lab_director', '-m', msg,
                   '--deliver', '--channel', 'feishu', '--timeout', '300']
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                log.info(f'Dispatching {task_id} to Lab Director (attempt {attempt})...')
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=310)
                if result.returncode == 0:
                    log.info(f'✅ {task_id} dispatched to Lab Director')
                    return
                err_msg = result.stderr[:200] if result.stderr else result.stdout[:200]
                log.warning(f'⚠️ {task_id} dispatch failed (attempt {attempt}): {err_msg}')
                if attempt < max_retries:
                    import time
                    wait = 5 * attempt
                    log.info(f'⏳ Retrying in {wait}s...')
                    time.sleep(wait)
            log.error(f'❌ {task_id} dispatch failed after {max_retries} retries')
        except subprocess.TimeoutExpired:
            log.error(f'❌ {task_id} dispatch timeout (310s)')
        except Exception as e:
            log.warning(f'⚠️ {task_id} dispatch error: {e}')
    
    threading.Thread(target=dispatch_to_agent, daemon=True).start()

    return {'ok': True, 'taskId': task_id, 'message': f'Directive {task_id} created, dispatching to Lab Director'}


def handle_review_action(task_id, action, comment=''):
    """Review Board action: approve or reject."""
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    if task.get('state') not in ('Review', 'Menxia'):
        return {'ok': False, 'error': f'Task {task_id} state is {task.get("state")}, cannot review'}

    if action == 'approve':
        if task['state'] == 'Menxia':
            task['state'] = 'Assigned'
            task['now'] = 'Review approved, forwarding to Operations Office'
            remark = f'✅ Approved: {comment or "Review passed"}'
            to_dept = 'Operations Office'
        else:
            task['state'] = 'Done'
            task['now'] = 'Review approved, task complete'
            remark = f'✅ Approved: {comment or "Review passed"}'
            to_dept = 'Human User'
    elif action == 'reject':
        round_num = (task.get('review_round') or 0) + 1
        task['review_round'] = round_num
        task['state'] = 'Zhongshu'
        task['now'] = f'Rejected, back to Planning Office (round {round_num})'
        remark = f'🚫 Rejected: {comment or "Needs revision"}'
        to_dept = 'Planning Office'
    else:
        return {'ok': False, 'error': f'Unknown action: {action}'}

    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': 'Review Board' if task.get('state') != 'Done' else 'Human User',
        'to': to_dept,
        'remark': remark
    })
    task['updatedAt'] = now_iso()
    save_tasks(tasks)

    new_state = task['state']
    if new_state != 'Done':
        dispatch_for_state(task_id, task, new_state)

    label = 'approved' if action == 'approve' else 'rejected'
    dispatched = ' (auto-dispatched)' if new_state != 'Done' else ''
    return {'ok': True, 'message': f'{task_id} {label}{dispatched}'}


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.info(f'{self.address_string()} - {format % args}')

    def do_OPTIONS(self):
        self.send_response(200)
        cors_headers(self)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            self.serve_file(BASE / 'dashboard.html')
        elif path == '/api/live-status':
            self.serve_json(DATA / 'live_status.json', {})
        elif path == '/api/agent-config':
            self.serve_json(DATA / 'agent_config.json', {})
        elif path == '/api/model-change-log':
            self.serve_json(DATA / 'model_change_log.json', [])
        elif path == '/api/last-result':
            self.serve_json(DATA / 'last_model_change_result.json', {})
        elif path == '/api/agents-status':
            self.serve_json_data(get_agents_status())
        else:
            self.send_error(404, 'Not Found')

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > MAX_REQUEST_BODY:
            self.send_error(413, 'Payload Too Large')
            return

        body = self.rfile.read(content_length).decode('utf-8') if content_length else '{}'
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON')
            return

        if path == '/api/set-model':
            self.handle_set_model(data)
        elif path == '/api/create-task':
            result = handle_create_task(
                data.get('title', ''),
                data.get('org', 'Planning Office'),
                data.get('official', 'Planning Director'),
                data.get('priority', 'normal'),
                data.get('templateId', ''),
                data.get('params', {}),
                data.get('targetDept', '')
            )
            self.send_json(result)
        elif path == '/api/task-action':
            result = handle_task_action(
                data.get('taskId', ''),
                data.get('action', ''),
                data.get('reason', '')
            )
            self.send_json(result)
        elif path == '/api/archive-task':
            result = handle_archive_task(
                data.get('taskId', ''),
                data.get('archived', False),
                data.get('archiveAllDone', False)
            )
            self.send_json(result)
        elif path == '/api/update-todos':
            result = update_task_todos(
                data.get('taskId', ''),
                data.get('todos', [])
            )
            self.send_json(result)
        elif path == '/api/review-action':
            result = handle_review_action(
                data.get('taskId', ''),
                data.get('action', ''),
                data.get('comment', '')
            )
            self.send_json(result)
        elif path == '/api/read-skill':
            result = read_skill_content(
                data.get('agentId', ''),
                data.get('skillName', '')
            )
            self.send_json(result)
        elif path == '/api/add-skill':
            result = add_skill_to_agent(
                data.get('agentId', ''),
                data.get('skillName', ''),
                data.get('description', ''),
                data.get('trigger', '')
            )
            self.send_json(result)
        else:
            self.send_error(404, 'Not Found')

    def serve_file(self, path):
        if not path.exists():
            self.send_error(404, 'File Not Found')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        cors_headers(self)
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def serve_json(self, path, default):
        data = read_json(path, default)
        self.send_json(data)

    def serve_json_data(self, data):
        self.send_json(data)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        cors_headers(self)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def handle_set_model(self, data):
        agent_id = data.get('agentId', '').strip()
        model = data.get('model', '').strip()
        if not agent_id or not model:
            self.send_json({'ok': False, 'error': 'Missing agentId or model'})
            return
        pending = read_json(DATA / 'pending_model_changes.json', [])
        pending.append({'agentId': agent_id, 'model': model, 'requestedAt': now_iso()})
        atomic_json_write(DATA / 'pending_model_changes.json', pending)
        log.info(f'Model change requested: {agent_id} → {model}')
        self.send_json({'ok': True, 'message': f'Model change queued for {agent_id}'})


def main():
    parser = argparse.ArgumentParser(description='OPMALab Kanban Server')
    parser.add_argument('--port', type=int, default=9731, help='Server port')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Bind address')
    parser.add_argument('--cors', type=str, default=None, help='Allowed CORS origin')
    args = parser.parse_args()

    global ALLOWED_ORIGIN
    ALLOWED_ORIGIN = args.cors

    server = HTTPServer((args.host, args.port), RequestHandler)
    log.info(f'OPMALab Kanban Server starting → http://{args.host}:{args.port}')
    print(f'\n🧪 OPMALab Dashboard: http://{args.host}:{args.port}\n')
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('Server shutting down...')
        server.shutdown()


if __name__ == '__main__':
    main()
