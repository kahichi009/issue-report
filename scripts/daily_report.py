import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
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


def fetch_project_items(owner, project_number, query=None):
    """ghコマンドでプロジェクトのアイテムをJSON形式で取得する"""
    cmd = [
        "gh", "project", "item-list",
        str(project_number),
        "--owner", owner,
        "--format", "json",
        "--limit", "100"
    ]

    if query:
        cmd.extend(["--query", query])

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


def get_update_summary(url, item_type):
    """ghコマンドでIssue/PRの最新コメントもしくは最新イベントを取得し、概要として利用する"""
    if not url:
        return "Draft要素が更新されました"

    sub_command = "pr" if item_type == "PullRequest" else "issue"
    cmd = ["gh", sub_command, "view", url, "--json", "comments"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        comments = data.get("comments", [])
        if comments:
            latest_comment = comments[-1].get("body", "")
            latest_comment = latest_comment.replace("\r\n", " ").replace("\n", " ").strip()
            # 50文字に切り詰める
            if len(latest_comment) > 50:
                latest_comment = latest_comment[:47] + "..."
            return f"💬 コメント: {latest_comment}"
        
        # コメントが無い場合は、イベント一覧を取得して最後のイベントを見る
        match = re.search(r"github\.com/([^/]+/[^/]+)/(issues|pull)/(\d+)", url)
        if match:
            repo_path = match.group(1)
            number = match.group(3)
            # 最新のイベントを1つ取得
            events_cmd = ["gh", "api", f"repos/{repo_path}/issues/{number}/events", "--jq", ".[-1]"]
            ev_result = subprocess.run(events_cmd, capture_output=True, text=True, check=False)
            if ev_result.returncode == 0 and ev_result.stdout.strip() and ev_result.stdout.strip() != "null":
                try:
                    last_event = json.loads(ev_result.stdout)
                    event_type = last_event.get("event")
                    
                    if event_type == "labeled":
                        label_name = last_event.get("label", {}).get("name", "Unknown")
                        return f"🏷️ ラベル追加 ({label_name})"
                    elif event_type == "unlabeled":
                        label_name = last_event.get("label", {}).get("name", "Unknown")
                        return f"🏷️ ラベル外れ ({label_name})"
                    elif event_type in ("closed", "reopened"):
                        return f"🔄 Issueが {event_type} されました"
                    elif event_type == "project_v2_item_status_changed":
                        return "📊 Projectステータスが変更されました"
                    elif event_type in ("assigned", "unassigned"):
                        return "👤 担当者が変更されました"
                    elif event_type == "renamed":
                        return "✏️ タイトルが変更されました"
                    else:
                        return f"⚙️ イベント発生: {event_type}"
                except json.JSONDecodeError:
                    pass

        return "更新あり (本文の編集など)"
    except Exception:
        return "更新あり"


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
