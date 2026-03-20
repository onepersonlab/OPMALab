#!/usr/bin/env python3
"""
Kanban Task Update Tool - Called by OPMALab agents

Usage:
  # Create task (when receiving directive)
  python3 kanban_update.py create OPL-20260320-001 "Task Title" PlanningOffice PlanningOffice Director

  # Update task state
  python3 kanban_update.py state OPL-20260320-001 Review "Plan submitted for review"

  # Add flow record
  python3 kanban_update.py flow OPL-20260320-001 "Planning Office" "Review Board" "Plan submitted for approval"

  # Mark task done
  python3 kanban_update.py done OPL-20260320-001 "/path/to/output" "Task completion summary"

  # Add/update todo item
  python3 kanban_update.py todo OPL-20260320-001 1 "Implement API interface" in-progress
  python3 kanban_update.py todo OPL-20260320-001 1 "" completed

  # 🔥 Real-time progress report - Agent calls this actively, doesn't change state, only updates now + todos
  python3 kanban_update.py progress OPL-20260320-001 "Analyzing requirements, drafting 3 sub-plans" "1. Research tech stack✅|2. Write design doc🔄|3. Build prototype"
"""
import json, pathlib, datetime, sys, subprocess, logging, os, re

_BASE = pathlib.Path(__file__).resolve().parent.parent
TASKS_FILE = _BASE / 'data' / 'tasks_source.json'
REFRESH_SCRIPT = _BASE / 'scripts' / 'refresh_live_data.py'

log = logging.getLogger('kanban')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

# Import atomic operations - agents only read/write via tasks_source.json
from file_lock import atomic_json_read, atomic_json_update, atomic_json_write  # noqa: E402

# State to organization mapping for OPMALab
STATE_ORG_MAP = {
    'Inbox': 'Inbox', 'Taizi': 'Lab Director', 'Zhongshu': 'Planning Office', 
    'Menxia': 'Review Board', 'Assigned': 'Operations Office',
    'Doing': 'In Progress', 'Review': 'Operations Office', 'Done': 'Done', 'Blocked': 'Blocked',
}

_STATE_AGENT_MAP = {
    'Taizi': 'lab_director',
    'Zhongshu': 'planning_office',
    'Menxia': 'review_board',
    'Assigned': 'operations_office',
    'Review': 'operations_office',
    'Pending': 'planning_office',
}

_ORG_AGENT_MAP = {
    'PI-CS': 'pi_cs', 'PI-Chem': 'pi_chem', 'PI-Bio': 'pi_bio',
    'PI-Mat': 'pi_mat', 'PI-Med': 'pi_med', 'PI-Agr': 'pi_agr', 
    'PI-Env': 'pi_env', 'PI-Eng': 'pi_eng',
    'Planning Office': 'planning_office', 'Review Board': 'review_board', 
    'Operations Office': 'operations_office',
}

_AGENT_LABELS = {
    'lab_director': 'Lab Director', 'planning_office': 'Planning Office', 
    'review_board': 'Review Board', 'operations_office': 'Operations Office',
    'pi_cs': 'PI-CS', 'pi_chem': 'PI-Chem', 'pi_bio': 'PI-Bio',
    'pi_mat': 'PI-Mat', 'pi_med': 'PI-Med', 'pi_agr': 'PI-Agr', 
    'pi_env': 'PI-Env', 'pi_eng': 'PI-Eng',
}

MAX_PROGRESS_LOG = 100

def load():
    return atomic_json_read(TASKS_FILE, [])

def save(tasks):
    atomic_json_write(TASKS_FILE, tasks)
    # Trigger refresh after write
    try:
        subprocess.Popen(['python3', str(REFRESH_SCRIPT)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')

def find_task(tasks, task_id):
    return next((t for t in tasks if t.get('id') == task_id), None)


_MIN_TITLE_LEN = 6
_JUNK_TITLES = {
    '?', '？', 'ok', 'yes', 'no', 'got it', 'received', 'thanks',
    'test', 'testing', 'hello', 'hi',
}

def _sanitize_text(raw, max_len=80):
    """Clean text: strip file paths, URLs, Conversation metadata, directive prefixes, truncate long content."""
    t = (raw or '').strip()
    # 1) Remove Conversation info / Conversation section
    t = re.split(r'\n*Conversation\b', t, maxsplit=1)[0].strip()
    # 2) Remove ```json code blocks
    t = re.split(r'\n*```', t, maxsplit=1)[0].strip()
    # 3) Remove Unix/Mac paths (/Users/xxx, /home/xxx, /opt/xxx, ./xxx)
    t = re.sub(r'[/\\~][A-Za-z0-9_\-.]+(?:\.(?:py|js|ts|json|md|sh|yaml|yml|txt|csv|html|css|log))?', '', t)
    # 4) Remove URLs
    t = re.sub(r'https?://\S+', '', t)
    # 5) Remove directive prefixes: "Directive:", "Order:" etc.
    t = re.sub(r'^(Directive|Order|Task)([[(][^)]]*[)])?[:\s]*', '', t, flags=re.IGNORECASE)
    # 6) Remove system metadata
    t = re.sub(r'(message_id|session_id|chat_id|open_id|user_id|tenant_key)\s*[:=]\s*\S+', '', t)
    # 7) Normalize whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    # 8) Truncate if too long
    if len(t) > max_len:
        t = t[:max_len] + '…'
    return t


def _sanitize_title(raw):
    """Sanitize title (max 80 chars)."""
    return _sanitize_text(raw, 80)


def _sanitize_remark(raw):
    """Sanitize flow remark (max 120 chars)."""
    return _sanitize_text(raw, 120)


def _infer_agent_id_from_runtime(task=None):
    """Infer the agent ID executing this command."""
    for k in ('OPENCLAW_AGENT_ID', 'OPENCLAW_AGENT', 'AGENT_ID'):
        v = (os.environ.get(k) or '').strip()
        if v:
            return v

    cwd = str(pathlib.Path.cwd())
    m = re.search(r'workspace-([a-zA-Z0-9_\-]+)', cwd)
    if m:
        return m.group(1)

    fpath = str(pathlib.Path(__file__).resolve())
    m2 = re.search(r'workspace-([a-zA-Z0-9_\-]+)', fpath)
    if m2:
        return m2.group(1)

    if task:
        state = task.get('state', '')
        org = task.get('org', '')
        aid = _STATE_AGENT_MAP.get(state)
        if aid is None and state in ('Doing', 'Next'):
            aid = _ORG_AGENT_MAP.get(org)
        if aid:
            return aid
    return ''


def _is_valid_task_title(title):
    """Validate if title is sufficient for a directive task."""
    t = (title or '').strip()
    if len(t) < _MIN_TITLE_LEN:
        return False, f'Title too short ({len(t)}<{_MIN_TITLE_LEN} chars), likely not a directive'
    if t.lower() in _JUNK_TITLES:
        return False, f'Title "{t}" is not a valid directive'

    if re.fullmatch(r'[\s??!!.…,·\-—~]+', t):
        return False, 'Title contains only punctuation'

    if re.match(r'^[/\\~.]', t) or re.search(r'/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+', t):
        return False, 'Title looks like a file path, please summarize task in plain language'
    # After sanitization, should not be empty
    if re.fullmatch(r'[\s\W]*', t):
        return False, 'Title is empty after sanitization'
    return True, ''


def cmd_create(task_id, title, state, org, official, remark=None):
    """Create task (called immediately when receiving directive)"""
    # Sanitize title (remove paths, URLs, metadata)
    title = _sanitize_title(title)

    valid, reason = _is_valid_task_title(title)
    if not valid:
        log.warning(f'⚠️ Refused to create {task_id}: {reason}')
        print(f'[Kanban] Refused to create: {reason}', flush=True)
        return
    actual_org = STATE_ORG_MAP.get(state, org)
    clean_remark = _sanitize_remark(remark) if remark else f"Directive: {title}"
    def modifier(tasks):
        existing = next((t for t in tasks if t.get('id') == task_id), None)
        if existing:
            if existing.get('state') in ('Done', 'Cancelled'):
                log.warning(f'⚠️ Task {task_id} is already completed (state={existing["state"]}), cannot overwrite')
                return tasks
            if existing.get('state') not in (None, '', 'Inbox', 'Pending'):
                log.warning(f'Task {task_id} already exists (state={existing["state"]}), will be overwritten')
        tasks = [t for t in tasks if t.get('id') != task_id]
        tasks.insert(0, {
            "id": task_id, "title": title, "official": official,
            "org": actual_org, "state": state,
            "now": clean_remark[:60] if remark else f"Directive received, waiting for {actual_org}",
            "eta": "-", "block": "None", "output": "", "ac": "",
            "flow_log": [{"at": now_iso(), "from": "Human User", "to": actual_org, "remark": clean_remark}],
            "updatedAt": now_iso()
        })
        return tasks
    atomic_json_update(TASKS_FILE, modifier, [])
    save(load())  # trigger refresh
    log.info(f'✅ Created {task_id} | {title[:30]} | state={state}')


def cmd_state(task_id, new_state, now_text=None):
    """Update task state (atomic operation)"""
    old_state = [None]
    def modifier(tasks):
        t = find_task(tasks, task_id)
        if not t:
            log.error(f'Task {task_id} does not exist')
            return tasks
        old_state[0] = t['state']
        t['state'] = new_state
        if new_state in STATE_ORG_MAP:
            t['org'] = STATE_ORG_MAP[new_state]
        if now_text:
            t['now'] = now_text
        t['updatedAt'] = now_iso()
        return tasks
    atomic_json_update(TASKS_FILE, modifier, [])
    save(load())  # trigger refresh
    log.info(f'✅ {task_id} state updated: {old_state[0]} → {new_state}')


def cmd_flow(task_id, from_dept, to_dept, remark):
    """Add flow record (atomic operation)"""
    clean_remark = _sanitize_remark(remark)
    def modifier(tasks):
        t = find_task(tasks, task_id)
        if not t:
            log.error(f'Task {task_id} does not exist')
            return tasks
        t.setdefault('flow_log', []).append({
            "at": now_iso(), "from": from_dept, "to": to_dept, "remark": clean_remark
        })
        t['updatedAt'] = now_iso()
        return tasks
    atomic_json_update(TASKS_FILE, modifier, [])
    save(load())  # trigger refresh
    log.info(f'✅ {task_id} flow: {from_dept} → {to_dept}')


def cmd_done(task_id, output_path='', summary=''):
    """Mark task as done (atomic operation)"""
    def modifier(tasks):
        t = find_task(tasks, task_id)
        if not t:
            log.error(f'Task {task_id} does not exist')
            return tasks
        t['state'] = 'Done'
        t['output'] = output_path
        t['now'] = summary or 'Task completed'
        t.setdefault('flow_log', []).append({
            "at": now_iso(), "from": t.get('org', 'Executing Dept'),
            "to": "Human User", "remark": f"✅ Done: {summary or 'Task completed'}"
        })
        t['updatedAt'] = now_iso()
        return tasks
    atomic_json_update(TASKS_FILE, modifier, [])
    save(load())  # trigger refresh
    log.info(f'✅ {task_id} completed')


def cmd_block(task_id, reason):
    """Mark as blocked (atomic operation)"""
    def modifier(tasks):
        t = find_task(tasks, task_id)
        if not t:
            log.error(f'Task {task_id} does not exist')
            return tasks
        t['state'] = 'Blocked'
        t['block'] = reason
        t['updatedAt'] = now_iso()
        return tasks
    atomic_json_update(TASKS_FILE, modifier, [])
    save(load())  # trigger refresh
    log.warning(f'⚠️ {task_id} blocked: {reason}')


def cmd_progress(task_id, now_text, todos_pipe='', tokens=0, cost=0.0, elapsed=0):
    """🔥 Real-time progress report - Agent calls this actively, doesn't change state, only updates now + todos

    now_text: One-sentence description of current work (required)
    todos_pipe: Optional, pipe-separated todo list, format:
        "Completed items✅|In-progress items🔄|Planned items"
        - Ends with ✅ → completed
        - Ends with 🔄 → in-progress
        - Otherwise → not-started
    tokens: Optional, token count consumed
    cost: Optional, cost in USD
    elapsed: Optional, elapsed time in seconds
    """
    clean = _sanitize_remark(now_text)
    # Parse todos_pipe
    parsed_todos = None
    if todos_pipe:
        new_todos = []
        for i, item in enumerate(todos_pipe.split('|'), 1):
            item = item.strip()
            if not item:
                continue
            if item.endswith('✅'):
                status = 'completed'
                title = item[:-1].strip()
            elif item.endswith('🔄'):
                status = 'in-progress'
                title = item[:-1].strip()
            else:
                status = 'not-started'
                title = item
            new_todos.append({'id': str(i), 'title': title, 'status': status})
        if new_todos:
            parsed_todos = new_todos


    try:
        tokens = int(tokens) if tokens else 0
    except (ValueError, TypeError):
        tokens = 0
    try:
        cost = float(cost) if cost else 0.0
    except (ValueError, TypeError):
        cost = 0.0
    try:
        elapsed = int(elapsed) if elapsed else 0
    except (ValueError, TypeError):
        elapsed = 0

    done_cnt = [0]
    total_cnt = [0]
    def modifier(tasks):
        t = find_task(tasks, task_id)
        if not t:
            log.error(f'Task {task_id} does not exist')
            return tasks
        t['now'] = clean
        if parsed_todos is not None:
            t['todos'] = parsed_todos
        # Build progress log entry
        at = now_iso()
        agent_id = _infer_agent_id_from_runtime(t)
        agent_label = _AGENT_LABELS.get(agent_id, agent_id)
        log_todos = parsed_todos if parsed_todos is not None else t.get('todos', [])
        log_entry = {
            'at': at, 'agent': agent_id, 'agentLabel': agent_label,
            'text': clean, 'todos': log_todos,
            'state': t.get('state', ''), 'org': t.get('org', ''),
        }
        # Add resource usage if provided
        if tokens > 0:
            log_entry['tokens'] = tokens
        if cost > 0:
            log_entry['cost'] = cost
        if elapsed > 0:
            log_entry['elapsed'] = elapsed
        t.setdefault('progress_log', []).append(log_entry)
        # Keep progress_log bounded
        if len(t['progress_log']) > MAX_PROGRESS_LOG:
            t['progress_log'] = t['progress_log'][-MAX_PROGRESS_LOG:]
        t['updatedAt'] = at
        done_cnt[0] = sum(1 for td in t.get('todos', []) if td.get('status') == 'completed')
        total_cnt[0] = len(t.get('todos', []))
        return tasks
    atomic_json_update(TASKS_FILE, modifier, [])
    save(load())  # trigger refresh
    res_info = ''
    if tokens or cost or elapsed:
        res_info = f' [res: {tokens}tok/${cost:.4f}/{elapsed}s]'
    log.info(f'📡 {task_id} progress: {clean[:40]}... [{done_cnt[0]}/{total_cnt[0]}]{res_info}')

def cmd_todo(task_id, todo_id, title, status='not-started', detail=''):
    """Add or update todo item (atomic operation)

    status: not-started / in-progress / completed
    detail: Optional, detailed output/description for this todo (Markdown format)
    """
    # Validate status
    if status not in ('not-started', 'in-progress', 'completed'):
        status = 'not-started'
    result_info = [0, 0]
    def modifier(tasks):
        t = find_task(tasks, task_id)
        if not t:
            log.error(f'Task {task_id} does not exist')
            return tasks
        if 'todos' not in t:
            t['todos'] = []
        existing = next((td for td in t['todos'] if str(td.get('id')) == str(todo_id)), None)
        if existing:
            existing['status'] = status
            if title:
                existing['title'] = title
            if detail:
                existing['detail'] = detail
        else:
            item = {'id': todo_id, 'title': title, 'status': status}
            if detail:
                item['detail'] = detail
            t['todos'].append(item)
        t['updatedAt'] = now_iso()
        result_info[0] = sum(1 for td in t['todos'] if td.get('status') == 'completed')
        result_info[1] = len(t['todos'])
        return tasks
    atomic_json_update(TASKS_FILE, modifier, [])
    save(load())  # trigger refresh
    log.info(f'✅ {task_id} todo [{result_info[0]}/{result_info[1]}]: {todo_id} → {status}')

_CMD_MIN_ARGS = {
    'create': 6, 'state': 3, 'flow': 5, 'done': 2, 'block': 3, 'todo': 4, 'progress': 3,
}

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    cmd = args[0]
    if cmd in _CMD_MIN_ARGS and len(args) < _CMD_MIN_ARGS[cmd]:
        print(f'Error: "{cmd}" command requires at least {_CMD_MIN_ARGS[cmd]} args, got {len(args)}')
        print(__doc__)
        sys.exit(1)
    if cmd == 'create':
        cmd_create(args[1], args[2], args[3], args[4], args[5], args[6] if len(args)>6 else None)
    elif cmd == 'state':
        cmd_state(args[1], args[2], args[3] if len(args)>3 else None)
    elif cmd == 'flow':
        cmd_flow(args[1], args[2], args[3], args[4])
    elif cmd == 'done':
        cmd_done(args[1], args[2] if len(args)>2 else '', args[3] if len(args)>3 else '')
    elif cmd == 'block':
        cmd_block(args[1], args[2])
    elif cmd == 'todo':
        cmd_todo(args[1], args[2], args[3], args[4] if len(args)>4 else 'not-started', args[5] if len(args)>5 else '')
    elif cmd == 'progress':
        cmd_progress(args[1], args[2], args[3] if len(args)>3 else '', 
                     args[4] if len(args)>4 else 0, args[5] if len(args)>5 else 0.0, args[6] if len(args)>6 else 0)
    else:
        print(f'Unknown command: {cmd}')
        print(__doc__)
        sys.exit(1)
