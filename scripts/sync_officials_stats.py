#!/usr/bin/env python3
"""
Synchronize agent statistics → data/officials_stats.json
Scans sessions.json for token usage, calculates costs, aggregates task stats
"""
import json, pathlib, datetime, logging
from file_lock import atomic_json_write

log = logging.getLogger('officials')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
AGENTS_ROOT = pathlib.Path.home() / '.openclaw' / 'agents'
OPENCLAW_CFG = pathlib.Path.home() / '.openclaw' / 'openclaw.json'

# Model pricing (per 1M tokens, USD)
MODEL_PRICING = {
    'anthropic/claude-sonnet-4-6':  {'in': 3.0,  'out': 15.0, 'cr': 0.30, 'cw': 3.75},
    'anthropic/claude-opus-4-5':    {'in': 15.0, 'out': 75.0, 'cr': 1.50, 'cw': 18.75},
    'anthropic/claude-haiku-3-5':   {'in': 0.8,  'out': 4.0,  'cr': 0.08, 'cw': 1.0},
    'openai/gpt-4o':                {'in': 2.5,  'out': 10.0, 'cr': 1.25, 'cw': 0},
    'openai/gpt-4o-mini':           {'in': 0.15, 'out': 0.6,  'cr': 0.075, 'cw': 0},
    'google/gemini-2.0-flash':      {'in': 0.075,'out': 0.3,  'cr': 0,    'cw': 0},
    'google/gemini-2.5-pro':        {'in': 1.25, 'out': 10.0, 'cr': 0,    'cw': 0},
}

# OPMALab 12 agents
OFFICIALS = [
    {'id': 'lab_director',    'label': 'Lab Director',    'role': 'Lab Director',    'emoji': '🎓', 'rank': 'Coordination'},
    {'id': 'planning_office', 'label': 'Planning Office', 'role': 'Planning Director', 'emoji': '📋', 'rank': 'Coordination'},
    {'id': 'review_board',    'label': 'Review Board',    'role': 'Review Chair',      'emoji': '🔍', 'rank': 'Coordination'},
    {'id': 'operations_office', 'label': 'Operations Office', 'role': 'Operations Director', 'emoji': '📮', 'rank': 'Coordination'},
    {'id': 'pi_cs',   'label': 'PI-CS',   'role': 'Computer Science PI', 'emoji': '🖥️', 'rank': 'Discipline PI'},
    {'id': 'pi_chem', 'label': 'PI-Chem', 'role': 'Chemistry PI',        'emoji': '🧪', 'rank': 'Discipline PI'},
    {'id': 'pi_bio',  'label': 'PI-Bio',  'role': 'Biology PI',          'emoji': '🧬', 'rank': 'Discipline PI'},
    {'id': 'pi_mat',  'label': 'PI-Mat',  'role': 'Materials Science PI','emoji': '🔩', 'rank': 'Discipline PI'},
    {'id': 'pi_med',  'label': 'PI-Med',  'role': 'Medicine PI',         'emoji': '🏥', 'rank': 'Discipline PI'},
    {'id': 'pi_agr',  'label': 'PI-Agr',  'role': 'Agriculture PI',      'emoji': '🌾', 'rank': 'Discipline PI'},
    {'id': 'pi_env',  'label': 'PI-Env',  'role': 'Environmental Science PI', 'emoji': '🌍', 'rank': 'Discipline PI'},
    {'id': 'pi_eng',  'label': 'PI-Eng',  'role': 'Engineering PI',      'emoji': '⚙️', 'rank': 'Discipline PI'},
]

def rj(p, d):
    try: return json.loads(pathlib.Path(p).read_text())
    except Exception: return d


# Pre-load openclaw config once (avoid re-reading per agent)
_OPENCLAW_CACHE = None

def _load_openclaw_cfg():
    global _OPENCLAW_CACHE
    if _OPENCLAW_CACHE is None:
        _OPENCLAW_CACHE = rj(OPENCLAW_CFG, {})
    return _OPENCLAW_CACHE


def normalize_model(model_value, fallback='anthropic/claude-sonnet-4-6'):
    if isinstance(model_value, str) and model_value:
        return model_value
    if isinstance(model_value, dict):
        return model_value.get('primary') or model_value.get('id') or fallback
    return fallback

def get_model(agent_id):
    cfg = _load_openclaw_cfg()
    default = normalize_model(cfg.get('agents',{}).get('defaults',{}).get('model',{}), 'anthropic/claude-sonnet-4-6')
    for a in cfg.get('agents',{}).get('list',[]):
        if a.get('id') == agent_id:
            return normalize_model(a.get('model', default), default)
    return default

def scan_agent(agent_id):
    """Read token statistics from sessions.json (aggregate all sessions)"""
    sj = AGENTS_ROOT / agent_id / 'sessions' / 'sessions.json'
    if not sj.exists():
        return {'tokens_in':0,'tokens_out':0,'cache_read':0,'cache_write':0,'sessions':0,'last_active':None,'messages':0}
    
    data = rj(sj, {})
    tin = tout = cr = cw = 0
    last_ts = None
    
    for sid, v in data.items():
        tin += v.get('inputTokens', 0) or 0
        tout += v.get('outputTokens', 0) or 0
        cr  += v.get('cacheRead', 0) or 0
        cw  += v.get('cacheWrite', 0) or 0
        ts = v.get('updatedAt')
        if ts:
            try:
                t = datetime.datetime.fromtimestamp(ts/1000) if isinstance(ts,int) else datetime.datetime.fromisoformat(ts.replace('Z','+00:00'))
                if last_ts is None or t > last_ts: last_ts = t
            except Exception: pass
    
    # Estimate message count from most recent session JSONL
    msg_count = 0
    if data:
        try:
            sf_key = max(data.keys(), key=lambda k: data[k].get('updatedAt',0) or 0, default=None)
        except Exception:
            sf_key = None
    else:
        sf_key = None
    if sf_key and data[sf_key].get('sessionFile'):
        sf = AGENTS_ROOT / agent_id / 'sessions' / pathlib.Path(data[sf_key]['sessionFile']).name
        try:
            lines = sf.read_text(errors='ignore').splitlines()
            for ln in lines:
                try:
                    e = json.loads(ln)
                    if e.get('type') == 'message' and e.get('message',{}).get('role') == 'assistant':
                        msg_count += 1
                except Exception: pass
        except Exception: pass

    return {
        'tokens_in': tin, 'tokens_out': tout,
        'cache_read': cr, 'cache_write': cw,
        'sessions': len(data),
        'last_active': last_ts.strftime('%Y-%m-%d %H:%M') if last_ts else None,
        'messages': msg_count,
    }

def calc_cost(s, model):
    p = MODEL_PRICING.get(model, MODEL_PRICING['anthropic/claude-sonnet-4-6'])
    usd = (s['tokens_in']/1e6*p['in'] + s['tokens_out']/1e6*p['out']
         + s['cache_read']/1e6*p['cr'] + s['cache_write']/1e6*p['cw'])
    return round(usd, 4)

def get_task_stats(org_label, tasks):
    done   = [t for t in tasks if t.get('state')=='Done' and t.get('org')==org_label]
    active = [t for t in tasks if t.get('state') in ('Doing','Review','Assigned') and t.get('org')==org_label]
    fl = sum(1 for t in tasks for f in t.get('flow_log',[])
             if f.get('from')==org_label or f.get('to')==org_label)
    # Collect participated tasks (OPL prefix)
    participated = []
    for t in tasks:
        if not t['id'].startswith('OPL'): continue
        for f in t.get('flow_log',[]):
            if f.get('from')==org_label or f.get('to')==org_label:
                if t['id'] not in [x['id'] for x in participated]:
                    participated.append({'id':t['id'],'title':t.get('title',''),'state':t.get('state','')})
                break
    return {'tasks_done':len(done),'tasks_active':len(active),
            'flow_participations':fl,'participated_edicts':participated}

def get_hb(agent_id, live_tasks):
    for t in live_tasks:
        if t.get('sourceMeta',{}).get('agentId')==agent_id and t.get('heartbeat'):
            return t['heartbeat']
    return {'status':'idle','label':'⚪ Idle','ageSec':None}

def main():
    tasks = rj(DATA/'tasks_source.json', [])
    live  = rj(DATA/'live_status.json', {})
    live_tasks = live.get('tasks', [])

    result = []
    for off in OFFICIALS:
        model   = get_model(off['id'])
        ss      = scan_agent(off['id'])
        ts      = get_task_stats(off['label'], tasks)
        hb      = get_hb(off['id'], live_tasks)
        cost_usd = calc_cost(ss, model)

        result.append({
            **off,
            'model': model,
            'model_short': model.split('/')[-1] if isinstance(model, str) and '/' in model else model,
            'stats': ss,
            'cost': {'model': model, 'totalUsd': cost_usd},
            'tasks': ts,
            'heartbeat': hb,
        })

    payload = {
        'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'officials': result,
    }
    DATA.mkdir(exist_ok=True)
    atomic_json_write(DATA / 'officials_stats.json', payload)
    log.info(f'{len(result)} officials synced')


if __name__ == '__main__':
    main()
