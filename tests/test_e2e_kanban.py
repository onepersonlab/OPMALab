#!/usr/bin/env python3
"""End-to-end test for kanban_update.py: sanitization + creation + flow

Can be run with pytest or directly with python3.
"""
import sys, os, json, pathlib, pytest

# Add scripts directory to path (for file_lock import)
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
os.chdir(_SCRIPTS_DIR)
sys.path.insert(0, '.')

from kanban_update import (
    _sanitize_title, _sanitize_remark, _is_valid_task_title,
    cmd_create, cmd_flow, cmd_state, cmd_done, load, TASKS_FILE
)

# Ensure data directory exists (for CI environments)
data_dir = TASKS_FILE.parent
if data_dir.exists() and not data_dir.is_dir():
    data_dir.unlink()
data_dir.mkdir(parents=True, exist_ok=True)
if not TASKS_FILE.exists():
    TASKS_FILE.write_text('[]')


def _get_task(tid):
    return next((x for x in load() if x['id'] == tid), None)


@pytest.fixture(autouse=True)
def _backup_and_restore():
    """Backup data before each test, restore and cleanup test tasks after."""
    backup = TASKS_FILE.read_text()
    yield
    TASKS_FILE.write_text(backup)
    tasks = json.loads(TASKS_FILE.read_text())
    tasks = [t for t in tasks if not t.get('id', '').startswith('OPL-TEST-')]
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))


# ── TEST 1: Sanitize title (remove paths + Conversation metadata)
def test_dirty_title_cleaned():
    cmd_create('OPL-TEST-E2E-01',
        'Comprehensive review of /Users/bingsen/clawd/openclaw-sansheng-liubu/ project\nConversation info (xxx)',
        'Zhongshu', 'Planning Office', 'Planning Director',
        'Directive: review /Users/bingsen/clawd/ project')
    t = _get_task('OPL-TEST-E2E-01')
    assert t is not None, "Task should be created"
    assert '/Users' not in t['title'], f"Title should not contain path: {t['title']}"
    assert 'Conversation' not in t['title'], f"Title should not contain Conversation: {t['title']}"
    assert '/Users' not in t['flow_log'][0]['remark'], f"Remark should not contain path: {t['flow_log'][0]['remark']}"


# ── TEST 2: Reject pure path as title
def test_pure_path_rejected():
    cmd_create('OPL-TEST-E2E-02', '/Users/bingsen/clawd/openclaw-sansheng-liubu/', 'Zhongshu', 'Planning Office', 'Planning Director')
    assert _get_task('OPL-TEST-E2E-02') is None, "Pure path title should be rejected"


# ── TEST 3: Normal title accepted
def test_normal_title():
    cmd_create('OPL-TEST-E2E-03', 'Research industrial data analysis LLM applications', 'Zhongshu', 'Planning Office', 'Planning Director', 'Lab Director summarizing directive')
    t = _get_task('OPL-TEST-E2E-03')
    assert t is not None, "Normal task should be created"
    assert t['title'] == 'Research industrial data analysis LLM applications', f"Title should be preserved: {t['title']}"


# ── TEST 4: Flow remark is sanitized
def test_flow_remark_cleaned():
    cmd_create('OPL-TEST-E2E-04', 'Research industrial data analysis LLM applications', 'Zhongshu', 'Planning Office', 'Planning Director')
    cmd_flow('OPL-TEST-E2E-04', 'Lab Director', 'Planning Office', 'Directive forwarded: review /Users/bingsen/clawd/xxx project Conversation blah')
    t = _get_task('OPL-TEST-E2E-04')
    assert t is not None
    last_flow = t['flow_log'][-1]
    assert '/Users' not in last_flow['remark'], f"Remark should not contain path: {last_flow['remark']}"
    assert 'Conversation' not in last_flow['remark'], f"Remark should not contain Conversation: {last_flow['remark']}"


# ── TEST 5: Short title rejected
def test_short_title_rejected():
    cmd_create('OPL-TEST-E2E-05', 'OK', 'Zhongshu', 'Planning Office', 'Planning Director')
    assert _get_task('OPL-TEST-E2E-05') is None, "Short title should be rejected"


# ── TEST 6: Directive prefix stripped
def test_prefix_stripped():
    cmd_create('OPL-TEST-E2E-06', 'Directive: Write technical blog post about agent architecture', 'Zhongshu', 'Planning Office', 'Planning Director')
    t = _get_task('OPL-TEST-E2E-06')
    assert t is not None, "Task should be created"
    assert not t['title'].startswith('Directive'), f"Prefix should be stripped: {t['title']}"


# ── TEST 7: State update + org mapping
def test_state_update():
    cmd_create('OPL-TEST-E2E-07', 'Test state update and org linkage', 'Zhongshu', 'Planning Office', 'Planning Director')
    cmd_state('OPL-TEST-E2E-07', 'Menxia', 'Plan submitted to Review Board')
    t = _get_task('OPL-TEST-E2E-07')
    assert t is not None
    assert t['state'] == 'Menxia', f"State should be Menxia: {t['state']}"
    assert t['org'] == 'Review Board', f"Org should be Review Board: {t['org']}"


# ── TEST 8: Mark as done
def test_done():
    cmd_create('OPL-TEST-E2E-08', 'Test task completion marking', 'Zhongshu', 'Planning Office', 'Planning Director')
    cmd_done('OPL-TEST-E2E-08', '/tmp/output.md', 'Task completed')
    t = _get_task('OPL-TEST-E2E-08')
    assert t is not None
    assert t['state'] == 'Done', f"State should be Done: {t['state']}"


# ── TEST 9: Completed task cannot be overwritten
def test_done_not_overwritable():
    cmd_create('OPL-TEST-E2E-09', 'Test protection of completed tasks', 'Zhongshu', 'Planning Office', 'Planning Director')
    cmd_done('OPL-TEST-E2E-09', '/tmp/output.md', 'Task completed')
    cmd_create('OPL-TEST-E2E-09', 'Attempt to overwrite completed task', 'Zhongshu', 'Planning Office', 'Planning Director')
    t = _get_task('OPL-TEST-E2E-09')
    assert t is not None
    assert t['state'] == 'Done', f"Should still be Done: {t['state']}"


# ── Run with: python3 tests/test_e2e_kanban.py
if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
