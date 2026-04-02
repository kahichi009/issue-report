import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def check_gh_auth():
    """gh auth status を実行し、認証されているか確認する"""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print("エラー: GitHub CLI (gh) の認証が通っていません。")
            print("手動で 'gh auth login' を実行するか、環境変数 'GH_TOKEN' を正しく設定してください。")
            print("詳細: ", result.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print("エラー: 'gh' コマンドが見つかりません。GitHub CLI がインストールされているか確認してください。")
        sys.exit(1)


def load_config(config_path):
    if not os.path.exists(config_path):
        print(f"エラー: 設定ファイル {config_path} が見つかりません。")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_project_items(owner, project_number):
    """ghコマンドでプロジェクトのアイテムをJSON形式で取得する"""
    cmd = [
        "gh", "project", "item-list",
        str(project_number),
        "--owner", owner,
        "--format", "json",
        "--limit", "100"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data.get("items", [])
    except subprocess.CalledProcessError as e:
        print(f"エラー: Project {project_number} の取得に失敗しました。")
        return []
    except json.JSONDecodeError:
        print("エラー: GitHubからの出力が正しいJSON形式ではありませんでした。")
        return []


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def generate_weekly_report(config, output_dir):
    """今週の target_date を基準に、リポジトリ別の集計を行う"""
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    report_date_local = today.strftime("%Y-%m-%d")
    lines = [f"# 週次進捗サマリー ({report_date_local})", ""]

    projects = config.get("projects", [])
    
    for proj in projects:
        repo = proj.get("repo", "Unknown Repo")
        owner = proj.get("owner")
        project_number = proj.get("project_number")

        lines.append(f"## 📦 Repository: {repo}")

        items = fetch_project_items(owner, project_number)
        
        due_this_week_items = []
        completed_this_week_items = []
        overdue_items = []

        for item in items:
            item_repo = item.get("content", {}).get("repository")
            if item_repo and item_repo.lower() != repo.lower():
                continue

            target_date_str = item.get("target_date")
            if not target_date_str:
                continue

            target_date = parse_date(str(target_date_str))
            if not target_date:
                continue

            status = str(item.get("status", "")).lower()
            is_done = "done" in status or "完了" in status

            if start_of_week <= target_date <= end_of_week:
                due_this_week_items.append(item)
                if is_done:
                    completed_this_week_items.append(item)

            if not is_done and target_date < today:
                overdue_items.append(item)

        lines.append("### 📊 集計結果")
        lines.append("| 🟢完了予定のタスク | ✅完了タスク | 🔴遅延タスク |")
        lines.append("| :--------------: | :--------: | :--------: |")
        lines.append(f"| {len(due_this_week_items)} | {len(completed_this_week_items)} | {len(overdue_items)} |")
        lines.append("")

        lines.append("### 🟢 今週完了予定のタスク")
        if due_this_week_items:
            lines.append("| Title | Target Date | Link |")
            lines.append("| ----- | ----------- | ---- |")
            for task in due_this_week_items:
                title = str(task.get("title", "No Title")).replace("|", "\\|")
                t_date = str(task.get('target_date', '-'))
                url = task.get("content", {}).get("url", "")
                link_str = f"[Link]({url})" if url else "-"
                lines.append(f"| {title} | {t_date} | {link_str} |")
        else:
            lines.append("今週完了予定のタスクはありません。")
        lines.append("")

        lines.append("### 🔴 遅延タスク（期限超過かつ未完了）")
        if overdue_items:
            lines.append("| Title | Target Date | Status | Link |")
            lines.append("| ----- | ----------- | ------ | ---- |")
            for task in overdue_items:
                title = str(task.get("title", "No Title")).replace("|", "\\|")
                t_date = str(task.get('target_date', '-'))
                status_str = str(task.get('status', 'Unknown')).replace("|", "\\|")
                url = task.get("content", {}).get("url", "")
                link_str = f"[Link]({url})" if url else "-"
                lines.append(f"| {title} | {t_date} | {status_str} | {link_str} |")
        else:
            lines.append("現在遅延しているタスクはありません")
        
        lines.append("---\n")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    report_path = output_dir_path / f"{report_date_local}.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"週次レポートを作成しました: {report_path}")


def main():
    check_gh_auth()
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    config_path = base_dir / "config.json"
    output_dir = base_dir / "reports" / "weekly"
    
    config = load_config(config_path)
    generate_weekly_report(config, output_dir)


if __name__ == "__main__":
    main()
