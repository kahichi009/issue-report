import json
import os
import re
import subprocess
import sys

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
    except subprocess.CalledProcessError:
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
            if len(latest_comment) > 50:
                latest_comment = latest_comment[:47] + "..."
            return f"💬 コメント: {latest_comment}"
        
        match = re.search(r"github\.com/([^/]+/[^/]+)/(issues|pull)/(\d+)", str(url))
        if match:
            repo_path = match.group(1)
            number = match.group(3)
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
