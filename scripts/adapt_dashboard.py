#!/usr/bin/env python3
"""
Dashboard SciLab Adaptation Script
Replaces Three Departments and Six Ministries terminology with SciLab research terminology
"""

import re

FILE = '/home/auto/.openclaw/workspace-taizi/onepersonlab-agents/dashboard/dashboard.html'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Title replacements
replacements = [
    # Header
    ('军机处 · 三省六部总控台', 'SciLab Dashboard · Research Coordination Platform'),
    ('皇上视角 · 实时旨意追踪', 'PI-Principal View · Real-time Research Directive Tracking'),
    ('旨意', 'Research Directive'),
    ('旨意看板', 'Research Dashboard'),
    ('省部调度', 'Department Coordination'),
    ('官员总览', 'Team Overview'),
    ('模型配置', 'Model Configuration'),
    ('技能配置', 'Skills Configuration'),
    ('小任务', 'Sessions'),
    ('奏折阁', 'Archive'),
    ('旨库', 'Template Library'),
    ('天下要闻', 'Research News'),
    
    # Departments
    ('太子', 'Lab Director'),
    ('中书省', 'Planning Office'),
    ('门下省', 'Review Board'),
    ('尚书省', 'Operations Office'),
    ('户部', 'PI-Agr/Env'),
    ('礼部', 'PI-Docs'),
    ('兵部', 'PI-CS'),
    ('刑部', 'PI-Compliance'),
    ('工部', 'PI-Eng/Mat'),
    ('吏部', 'PI-HR'),
    ('皇上', 'PI-Principal'),
    ('六部', 'Discipline PIs'),
    ('早朝', 'Morning Briefing'),
    ('钦天监', 'News Aggregator'),
    
    # Action verbs
    ('下旨', 'Issue Directive'),
    ('分拣', 'Triage'),
    ('起草', 'Plan'),
    ('审议', 'Review'),
    ('派发', 'Assign'),
    ('执行', 'Execute'),
    ('汇总', 'Consolidate'),
    ('回奏', 'Report'),
    
    # Status labels
    ('收件', 'Inbox'),
    ('待处理', 'Pending'),
    ('太子分拣', 'Lab Director Triage'),
    ('中书起草', 'Planning'),
    ('门下审议', 'Review'),
    ('已派发', 'Assigned'),
    ('执行中', 'In Progress'),
    ('待审查', 'Pending Review'),
    ('已完成', 'Completed'),
    ('阻塞', 'Blocked'),
    ('已取消', 'Cancelled'),
    ('待执行', 'Ready'),
    
    # CSS classes (department colors)
    ('.dt-中书省', '.dt-PlanningOffice'),
    ('.dt-门下省', '.dt-ReviewBoard'),
    ('.dt-尚书省', '.dt-OperationsOffice'),
    ('.dt-礼部', '.dt-PI-Docs'),
    ('.dt-户部', '.dt-PI-Agr'),
    ('.dt-兵部', '.dt-PI-CS'),
    ('.dt-刑部', '.dt-PI-Compliance'),
    ('.dt-工部', '.dt-PI-Eng'),
    ('.dt-吏部', '.dt-PI-HR'),
    
    # State classes
    ('.st-Zhongshu', '.st-PlanningOffice'),
    ('.st-Taizi', '.st-LabDirector'),
    ('.st-Menxia', '.st-ReviewBoard'),
    ('.st-Assigned', '.st-OperationsOffice'),
    
    # Tab badges
    ('📜 旨意看板', '📋 Research Dashboard'),
    ('🔭 省部调度', '🔭 Dept Coordination'),
    ('👥 官员总览', '👥 Team Overview'),
    ('⚙️ 模型配置', '⚙️ Models'),
    ('🛠️ 技能配置', '🛠️ Skills'),
    ('💬 小任务', '💬 Sessions'),
    ('📜 奏折阁', '📚 Archive'),
    ('📜 旨库', '📖 Templates'),
    ('📰 天下要闻', '📰 News'),
    
    # Filters
    ('中书省', 'Planning'),
    ('尚书省', 'Operations'),
    ('礼部', 'Docs'),
    ('户部', 'Agr'),
    ('兵部', 'CS'),
    ('刑部', 'Compliance'),
    ('工部', 'Eng'),
    ('吏部', 'HR'),
    ('门下省', 'Review'),
    ('钦天监', 'News'),
    
    # Agent labels
    ("label:'太子'", "label:'Lab Director'"),
    ("label:'中书省'", "label:'Planning Office'"),
    ("label:'门下省'", "label:'Review Board'"),
    ("label:'尚书省'", "label:'Operations Office'"),
    ("label:'礼部'", "label:'Docs'"),
    ("label:'户部'", "label:'Agr'"),
    ("label:'兵部'", "label:'CS'"),
    ("label:'刑部'", "label:'Compliance'"),
    ("label:'工部'", "label:'Eng'"),
    ("label:'吏部'", "label:'HR'"),
    
    # Role descriptions
    ("role:'太子'", "role:'Research Coordinator'"),
    ("role:'中书令'", "role:'Planning Director'"),
    ("role:'侍中'", "role:'Review Chair'"),
    ("role:'尚书令'", "role:'Operations Director'"),
    ("role:'礼部尚书'", "role:'Documentation Lead'"),
    ("role:'户部尚书'", "role:'Resource Manager'"),
    ("role:'兵部尚书'", "role:'Engineering Lead'"),
    ("role:'刑部尚书'", "role:'Compliance Officer'"),
    ("role:'工部尚书'", "role:'Infrastructure Lead'"),
    ("role:'吏部尚书'", "role:'HR Manager'"),
    
    # Rank (keep simplified)
    ("rank:'储君'", "rank:'Coordinator'"),
    ("rank:'正一品'", "rank:'Director'"),
    ("rank:'正二品'", "rank:'Lead'"),
    
    # Misc
    ('各省部当前承接旨意与执行状态', 'Current research directives and execution status by department'),
    ('通过飞书向太子发送任务，太子分拣后转中书省处理', 'Send research directives via Feishu to Lab Director for triage and planning'),
    ('点击左侧官员查看详情', 'Click on a team member to view details'),
    ('参与旨意', 'Research Directives'),
    ('完成旨意', 'Completed Directives'),
    ('累计完成旨意', 'Total Completed'),
    ('道旨意', ' directives'),
    ('候命中', 'Standby'),
    ('最近参与', 'Last involved in'),
    ('尚无旨意记录', 'No directive records yet'),
    ('一键归档已完成', 'Archive All Completed'),
    ('已归档', 'Archived'),
    ('进行中', 'In Progress'),
    ('全部', 'All'),
    ('筛选', 'Filter'),
    ('同步中', 'Syncing'),
    ('立即刷新', 'Refresh'),
    ('变更记录', 'Change Log'),
    ('飞书/Telegram 中的日常对话与小任务 · 非 JJC 圣旨类任务', 'Daily conversations and small tasks via Feishu/Telegram - Non-directive sessions'),
    ('任务完成后自动生成奏折，记录从下旨到完成的完整过程', 'Automatically generated when directives complete - Full workflow from issue to completion'),
    ('更改后自动重启 Gateway（约 5 秒）', 'Gateway auto-restarts after changes (~5 sec)'),
    ('点击技能查看详情，底部可添加新技能', 'Click skill to view details, add new skills at bottom'),
    ('今日统计', "Today's Stats"),
    ('上朝仪式', 'Morning Ceremony'),
    ('功过簿', 'Performance Log'),
    ('御批模式', 'Manual Approval Mode'),
    ('急递铺', 'Message Flow'),
    ('国史馆', 'Knowledge Base'),
]

for old, new in replacements:
    content = content.replace(old, new)

# Fix DEPT_COLOR mapping
content = re.sub(
    r"const DEPT_COLOR = \{[^}]+\}",
    "const DEPT_COLOR = {'Lab Director':'#e8a040','Planning Office':'#a07aff','Review Board':'#6a9eff','Operations Office':'#6aef9a','PI-Docs':'#f5c842','PI-Agr':'#ff9a6a','PI-CS':'#ff5270','PI-Compliance':'#cc4444','PI-Eng':'#44aaff','PI-HR':'#9b59b6','PI-Principal':'#ffd700','Report':'#2ecc8a'}",
    content
)

# Fix STATE_LABEL mapping
content = re.sub(
    r"const STATE_LABEL=\{[^}]+\}",
    "const STATE_LABEL={Inbox:'Inbox',Pending:'Pending',LabDirector:'Lab Director Triage',PlanningOffice:'Planning',ReviewBoard:'Review',OperationsOffice:'Assigned',Doing:'In Progress',Review:'Pending Review',Done:'Completed',Blocked:'Blocked',Cancelled:'Cancelled',Next:'Ready'}",
    content
)

# Fix pipeline stages
content = re.sub(
    r"\{key:'Inbox'.+?\{key:'Next'.+?\}",
    """{key:'Inbox',    dept:'PI-Principal', icon:'👑', action:'Issue'},
  {key:'LabDirector',    dept:'Lab Director', icon:'🤴', action:'Triage'},
  {key:'PlanningOffice', dept:'Planning Office', icon:'📋', action:'Plan'},
  {key:'ReviewBoard',   dept:'Review Board', icon:'🔍', action:'Review'},
  {key:'OperationsOffice', dept:'Operations Office', icon:'📮', action:'Assign'},
  {key:'Doing',    dept:'Discipline PIs', icon:'🔬', action:'Execute'},
  {key:'Review',   dept:'Operations Office', icon:'🔎', action:'Consolidate'},
  {key:'Done', dept:'Report', icon:'✅', action:'Report'}""",
    content,
    flags=re.DOTALL
)

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("Dashboard adapted to SciLab terminology successfully!")
