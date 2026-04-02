import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from utils import check_gh_auth, load_config, fetch_project_items, get_update_summary


def generate_daily_report(config, output_dir):
    """直近更新されたアイテムを抽出し、リポジトリ単位の表形式でMarkdown化する"""
    now = datetime.now(timezone.utc)
    report_date_local = now.astimezone().strftime("%Y-%m-%d")
    
    # 昨日以降のアイテムをクエリとして与える
    query_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    query = f"updated:>={query_date}"

    lines = [f"# 日次進捗レポート ({report_date_local})", ""]
    has_updates = False

    projects = config.get("projects", [])
    for proj in projects:
        repo = proj.get("repo", "Unknown Repo")
        owner = proj.get("owner")
        project_number = proj.get("project_number")

        lines.append(f"## 📦 Repository: {repo}")
        
        items = fetch_project_items(owner, project_number, query)
        
        # このリポジトリに属するアイテムだけをフィルタリング
        repo_items = []
        for item in items:
            item_repo = item.get("content", {}).get("repository")
            if not item_repo or item_repo.lower() == repo.lower():
                repo_items.append(item)

        if not repo_items:
            lines.append("過去24時間以内に更新されたタスクはありません。")
            lines.append("")
            continue

        has_updates = True
        # テーブルヘッダー
        lines.append("| Assignee | Title | Status | Link | Update Summary |")
        lines.append("| -------- | ----- | ------ | ---- | -------------- |")

        for item in repo_items:
            assignees_data = item.get("assignees", [])
            assignee_names = [a.get("login") if isinstance(a, dict) else str(a) for a in assignees_data]
            assignee_str = ", ".join(assignee_names) if assignee_names else "Unassigned"

            title = str(item.get("title", "No Title"))
            status = str(item.get("status", "Unknown"))
            
            content = item.get("content", {})
            url = content.get("url", "")
            item_type = content.get("type", "Issue")
            link_str = f"[Link]({url})" if url else "-"
            
            # 更新概要を取得
            summary = get_update_summary(url, item_type)

            # Markdownの表が崩れないようにパイプ文字などをエスケープ
            title_escaped = title.replace("|", "\\|")
            summary_escaped = summary.replace("|", "\\|")

            lines.append(f"| {assignee_str} | {title_escaped} | {status} | {link_str} | {summary_escaped} |")
        
        lines.append("")

    if not has_updates:
        lines = [f"# 日次進捗レポート ({report_date_local})", "", "過去24時間以内に更新されたタスクはどのプロジェクトにもありませんでした。"]

    # 保存
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    report_path = output_dir_path / f"{report_date_local}.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"日次レポートを作成しました: {report_path}")


def main():
    check_gh_auth()
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    config_path = base_dir / "config.json"
    output_dir = base_dir / "reports" / "daily"
    
    config = load_config(config_path)
    generate_daily_report(config, output_dir)


if __name__ == "__main__":
    main()
