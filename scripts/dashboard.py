import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# PYTHONPATHを考慮してutilsをインポート
sys.path.append(str(Path(__file__).parent))
from utils import check_gh_auth, load_config, fetch_project_items, get_update_summary

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Projects Dashboard</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --success: #4ade80;
            --warning: #fbbf24;
            --danger: #f87171;
            --border: rgba(255, 255, 255, 0.1);
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', 'Segoe UI', sans-serif;
            margin: 0; padding: 20px 10px;
            font-size: 14px;
            background-image: radial-gradient(circle at top right, #1e293b, transparent 40%),
                              radial-gradient(circle at bottom left, #0f172a, transparent 40%);
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            display: flex; justify-content: space-between; align-items: flex-end;
            border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 20px;
        }
        .header h1 { margin: 0; font-size: 1.8em; background: -webkit-linear-gradient(45deg, var(--accent), var(--success)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header p { margin: 0; color: var(--text-muted); font-size: 0.9em; }
        
        .mode-badge {
            display: inline-block; padding: 4px 10px; border-radius: 12px; background: rgba(56, 189, 248, 0.2); border: 1px solid var(--accent); color: var(--accent); font-weight: bold; margin-left: 10px; font-size: 0.8em; vertical-align: middle;
        }
        
        .glass-card {
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            padding: 15px 20px;
            margin-bottom: 20px;
            transition: transform 0.2s;
        }
        .glass-card:hover { transform: translateY(-2px); }
        .card-title { margin-top: 0; font-size: 1.25em; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
        
        .stat-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 15px;
        }
        .stat-box {
            text-align: center; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);
        }
        .stat-box h3 { margin: 0 0 5px 0; font-size: 0.85em; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
        .stat-num { font-size: 2.2em; font-weight: 800; color: var(--text-main); line-height: 1; }
        .stat-num.alert { color: var(--danger); text-shadow: 0 0 10px rgba(248, 113, 113, 0.5); }
        .stat-num.good { color: var(--success); }
        .stat-num.warning { color: var(--warning); }
        
        table { width: 100%; border-collapse: collapse; font-size: 0.95em; }
        th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border); }
        th { color: var(--text-muted); font-weight: 500; text-transform: uppercase; font-size: 0.8em; letter-spacing: 0.5px; }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: rgba(255,255,255,0.02); }
        
        a { color: var(--accent); text-decoration: none; transition: opacity 0.2s; }
        a:hover { opacity: 0.8; text-decoration: underline; }
        
        .badge {
            display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 0.75em; font-weight: 600;
            background: rgba(255,255,255,0.1); margin-right: 4px; margin-bottom: 4px;
        }
        .badge.todo { background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }
        .badge.done { background: rgba(52, 211, 153, 0.2); color: #6ee7b7; border: 1px solid rgba(52, 211, 153, 0.3); }
        .badge.bug { background: rgba(248, 113, 113, 0.2); color: #fca5a5; border: 1px solid rgba(248, 113, 113, 0.3); }
        
        .empty-state { text-align: center; color: var(--text-muted); padding: 20px; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 GitHub Projects Dashboard {mode_badge}</h1>
            <p>Last Updated: {date}</p>
        </div>
        {content}
    </div>
</body>
</html>
"""

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

def generate_dashboard(mode="target_date"):
    check_gh_auth()
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    config = load_config(base_dir / "config.json")
    
    today = datetime.now(timezone.utc).date()
    now_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    cards_html = []
    
    for proj in config.get("projects", []):
        proj_modes = proj.get("modes", ["target_date", "sprint"])
        if mode not in proj_modes:
            continue
            
        repo = proj.get("repo", "Unknown Repo")
        owner = proj.get("owner")
        project_number = proj.get("project_number")
        
        items = fetch_project_items(owner, project_number)
        
        total_count = 0
        overdue_items = []
        due_this_week_items = []
        
        done_items = []
        in_progress_items = []
        todo_items = []
        
        table_rows = []
        
        for item in items:
            item_repo = item.get("content", {}).get("repository")
            if item_repo and item_repo.lower() != repo.lower():
                continue
            
            total_count += 1
            
            status = str(item.get("status", "")).lower()
            is_done = "done" in status or "完了" in status
            is_in_progress = "progress" in status or "進行中" in status
            
            if mode == "sprint":
                if is_done:
                    done_items.append(item)
                elif is_in_progress:
                    in_progress_items.append(item)
                else:
                    todo_items.append(item)
                    
                is_overdue = False # Disabled in sprint mode
                should_render_table = not is_done
            else:
                target_date_str = item.get("target_date")
                target_date = parse_date(str(target_date_str)) if target_date_str else None
                
                is_overdue = False
                if target_date and not is_done and target_date < today:
                    is_overdue = True
                    overdue_items.append(item)
                
                if target_date and start_of_week <= target_date <= end_of_week and not is_done:
                    due_this_week_items.append(item)
                
                should_render_table = (target_date and start_of_week <= target_date <= end_of_week) or is_overdue
                
            if should_render_table:
                title = str(item.get("title", "No Title"))
                url = item.get("content", {}).get("url", "#")
                
                status_class = "done" if is_done else "todo"
                status_badge = f'<span class="badge {status_class}">{item.get("status", "?")}</span>'
                
                labels_html = ""
                for l in item.get("labels", []):
                    lname = l if isinstance(l, str) else l.get("name", str(l))
                    lclass = "bug" if "bug" in lname.lower() else ""
                    labels_html += f'<span class="badge {lclass}">{lname}</span>'
                
                assignees_data = item.get("assignees", [])
                assignee_names = [a.get("login") if isinstance(a, dict) else str(a) for a in assignees_data]
                assignee_str = ", ".join(assignee_names) if assignee_names else "Unassigned"
                
                if mode == "target_date":
                    target_date_str = item.get("target_date", "-")
                    date_visual = f'<span style="color:var(--danger)">{target_date_str} (遅延)</span>' if is_overdue else str(target_date_str)
                else:
                    date_visual = "-"
                    
                row_html = f"<tr><td>{assignee_str}</td><td><a href='{url}' target='_blank'>{title}</a></td><td>{status_badge}</td><td>{labels_html}</td><td>{date_visual}</td></tr>"
                table_rows.append(row_html)
        
        table_content = "".join(table_rows) if table_rows else "<tr><td colspan='5' class='empty-state'>今対応すべきタスクはありません 🎉</td></tr>"
        
        if mode == "sprint":
            todo_num = len(todo_items)
            class_todo = "alert" if todo_num > 0 else "good"
            
            card = f"""
            <div class="glass-card">
                <h2 class="card-title">📦 {repo}</h2>
                <div class="stat-grid">
                    <div class="stat-box">
                        <h3>Done</h3>
                        <div class="stat-num good">{len(done_items)}</div>
                    </div>
                    <div class="stat-box">
                        <h3>In Progress</h3>
                        <div class="stat-num warning">{len(in_progress_items)}</div>
                    </div>
                    <div class="stat-box">
                        <h3>Todo / Other</h3>
                        <div class="stat-num {class_todo}">{todo_num}</div>
                    </div>
                </div>
                
                <h3>📋 Action Required (In Progress / Todo)</h3>
                <table>
                    <tr><th>Assignee</th><th>Issue Title</th><th>Status</th><th>Labels</th><th>Target Date</th></tr>
                    {table_content}
                </table>
            </div>
            """
        else:
            overdue_num = len(overdue_items)
            class_overdue = "alert" if overdue_num > 0 else "good"
            
            card = f"""
            <div class="glass-card">
                <h2 class="card-title">📦 {repo}</h2>
                <div class="stat-grid">
                    <div class="stat-box">
                        <h3>Total Active Issues</h3>
                        <div class="stat-num">{total_count}</div>
                    </div>
                    <div class="stat-box">
                        <h3>Due This Week</h3>
                        <div class="stat-num">{len(due_this_week_items)}</div>
                    </div>
                    <div class="stat-box">
                        <h3>Overdue Tasks</h3>
                        <div class="stat-num {class_overdue}">{overdue_num}</div>
                    </div>
                </div>
                
                <h3>📋 Action Required (Due / Overdue)</h3>
                <table>
                    <tr><th>Assignee</th><th>Issue Title</th><th>Status</th><th>Labels</th><th>Target Date</th></tr>
                    {table_content}
                </table>
            </div>
            """
        cards_html.append(card)
        
    final_content = "".join(cards_html)
    if not final_content:
        final_content = "<div class='glass-card empty-state'>No Project Configurations Found.</div>"
        
    mode_str = "TARGET DATE MODE" if mode == "target_date" else "SPRINT MODE"
    mode_badge = f'<span class="mode-badge">{mode_str}</span>'
    html = HTML_TEMPLATE.replace("{date}", now_str).replace("{content}", final_content).replace("{mode_badge}", mode_badge)

    
    out_dir = base_dir / "reports" / "dashboard"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    filename = "index.html" if mode == "target_date" else f"index_{mode}.html"
    out_path = out_dir / filename
    
    with out_path.open("w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"ダッシュボードを生成しました (Mode: {mode}): {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["target_date", "sprint"], default="target_date")
    args = parser.parse_args()
    generate_dashboard(mode=args.mode)
