#!/usr/bin/env python3
"""
Sync OpenClaw runtime sessions → data/tasks_source.json
Maps active sessions to task entries for dashboard display
"""
import json
import pathlib
import time
import datetime
import traceback
import logging
import re
from file_lock import atomic_json_write, atomic_json_read

log = logging.getLogger('sync_runtime')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
DATA.mkdir(exist_ok=True)
SYNC_STATUS = DATA / 'sync_status.json'
SESSIONS_ROOT = pathlib.Path.home() / '.openclaw' / 'agents'

# OPMALab agent mapping
OFFICIAL_MAP = {
    'lab_director':    ('Lab Director', 'Lab Director'),
    'planning_office': ('Planning Director', 'Planning Office'),
    'review_board':    ('Review Chair', 'Review Board'),
    'operations_office': ('Operations Director', 'Operations Office'),
    'pi_cs':   ('Computer Science PI', 'PI-CS'),
    'pi_chem': ('Chemistry PI', 'PI-Chem'),
    'pi_bio':  ('Biology PI', 'PI-Bio'),
    'pi_mat':  ('Materials Science PI', 'PI-Mat'),
    'pi_med':  ('Medicine PI', 'PI-Med'),
    'pi_agr':  ('Agriculture PI', 'PI-Agr'),
    'pi_env':  ('Environmental Science PI', 'PI-Env'),
    'pi_eng':  ('Engineering PI', 'PI-Eng'),
}


def write_status(**kwargs):
    atomic_json_write(SYNC_STATUS, kwargs)


def ms_to_str(ts_ms):
    if not ts_ms:
        return '-'
    try:
        return datetime.datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return '-'


def state_from_session(age_ms, aborted):
    if aborted:
        return 'Blocked'
    if age_ms <= 2 * 60 * 1000:
        return 'Doing'
    if age_ms <= 60 * 60 * 1000:
        return 'Review'
    return 'Next'


def detect_official(agent_id):
    return OFFICIAL_MAP.get(agent_id, ('Operations Director', 'Operations Office'))


def load_activity(session_file, limit=12):
    p = pathlib.Path(session_file or '')
    if not p.exists():
        return []
    rows = []
    try:
        lines = p.read_text(errors='ignore').splitlines()
    except Exception:
        return []

    # Read all valid JSON lines first
    events = []
    for ln in lines:
        try:
            item = json.loads(ln)
            events.append(item)
        except:
            continue

    # Process events to extract meaningful activity
    for item in reversed(events):
        msg = item.get('message') or {}
        role = msg.get('role')
        ts = item.get('timestamp') or ''

        if role == 'toolResult':
            tool = msg.get('toolName', '-')
            details = msg.get('details') or {}
            content = msg.get('content', [{'text': ''}])[0].get('text', '')
            if len(content) < 50:
                text = f"Tool '{tool}' returned: {content}"
            else:
                text = f"Tool '{tool}' finished"
            rows.append({'at': ts, 'kind': 'tool', 'text': text})

        elif role == 'assistant':
            text = ''
            for c in msg.get('content', []):
                if c.get('type') == 'text' and c.get('text'):
                    raw_text = c.get('text').strip()
                    clean_text = raw_text.replace('[[reply_to_current]]', '').strip()
                    if clean_text:
                        text = clean_text
                    break
            if text:
                summary = text.split('\n')[0]
                if len(summary) > 200:
                    summary = summary[:200] + '...'
                rows.append({'at': ts, 'kind': 'assistant', 'text': summary})
                
        elif role == 'user':
            text = ''
            for c in msg.get('content', []):
                if c.get('type') == 'text':
                    text = c.get('text', '')[:100]
            if text:
                rows.append({'at': ts, 'kind': 'user', 'text': f"User: {text}..."})

        if len(rows) >= limit:
            break

    return rows


def build_task(agent_id, session_key, row, now_ms):
    session_id = row.get('sessionId') or session_key
    updated_at = row.get('updatedAt') or 0
    age_ms = max(0, now_ms - updated_at) if updated_at else 99 * 24 * 3600 * 1000
    aborted = bool(row.get('abortedLastRun'))
    state = state_from_session(age_ms, aborted)

    official, org = detect_official(agent_id)
    channel = row.get('lastChannel') or (row.get('origin') or {}).get('channel') or '-'
    session_file = row.get('sessionFile', '')
    
    # Build activity summary
    latest_act = 'Waiting for input'
    acts = load_activity(session_file, limit=5)
    
    if acts:
        first_act = acts[0]
        if first_act['kind'] == 'tool' and len(acts) > 1:
            for next_act in acts[1:]:
                if next_act['kind'] == 'assistant':
                    latest_act = f"Executing: {next_act['text'][:80]}"
                    break
            else:
                latest_act = first_act['text'][:60]
        elif first_act['kind'] == 'assistant':
            latest_act = f"Thinking: {first_act['text'][:80]}"
        else:
            latest_act = acts[0]['text'][:60]
    
    title_label = (row.get('origin') or {}).get('label') or session_key
    
    if re.match(r'agent:\w+:cron:', title_label):
        title = f"{org} Scheduled Task"
    elif re.match(r'agent:\w+:subagent:', title_label):
        title = f"{org} Subtask"
    elif title_label == session_key or len(title_label) > 40:
        title = f"{org} Session"
    else:
        title = f"{title_label}"
    
    return {
        'id': f"OPL-{agent_id}-{str(session_id)[:8]}",
        'title': title,
        'official': official,
        'org': org,
        'state': state,
        'now': latest_act,
        'eta': ms_to_str(updated_at),
        'block': 'Last run interrupted' if aborted else 'None',
        'output': session_file,
        'flow': {
            'draft': f"agent={agent_id}",
            'review': f"updatedAt={ms_to_str(updated_at)}",
            'dispatch': f"sessionKey={session_key}",
        },
        'ac': 'Real-time mapping from OpenClaw runtime sessions',
        'activity': load_activity(session_file, limit=10),
        'sourceMeta': {
            'agentId': agent_id,
            'sessionKey': session_key,
            'sessionId': session_id,
            'updatedAt': updated_at,
            'ageMs': age_ms,
            'systemSent': bool(row.get('systemSent')),
            'abortedLastRun': aborted,
            'inputTokens': row.get('inputTokens'),
            'outputTokens': row.get('outputTokens'),
            'totalTokens': row.get('totalTokens'),
        }
    }


def main():
    start = time.time()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    now_ms = int(time.time() * 1000)

    try:
        tasks = []
        scan_files = 0

        if SESSIONS_ROOT.exists():
            for agent_dir in sorted(SESSIONS_ROOT.iterdir()):
                if not agent_dir.is_dir():
                    continue
                agent_id = agent_dir.name
                
                # Only process OPMALab agents
                if agent_id not in OFFICIAL_MAP:
                    continue
                
                sessions_file = agent_dir / 'sessions' / 'sessions.json'
                if not sessions_file.exists():
                    continue
                
                scan_files += 1
                sessions_data = rj(sessions_file, {})
                
                for session_key, row in sessions_data.items():
                    task = build_task(agent_id, session_key, row, now_ms)
                    tasks.append(task)

        # Write to tasks_source.json
        atomic_json_write(DATA / 'tasks_source.json', tasks)
        
        duration_ms = int((time.time() - start) * 1000)
        write_status(
            ok=True,
            at=now,
            durationMs=duration_ms,
            tasksCount=len(tasks),
            filesScanned=scan_files,
        )
        log.info(f'Synced {len(tasks)} tasks from {scan_files} agents in {duration_ms}ms')

    except Exception as e:
        log.error(f'Sync failed: {e}')
        traceback.print_exc()
        write_status(
            ok=False,
            at=now,
            error=str(e),
        )


def rj(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


if __name__ == '__main__':
    main()
