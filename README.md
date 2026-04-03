# GitHub Project Issue Reporter

GitHub CLI (`gh`) を利用して、複数のリポジトリとGitHub Project (V2) の進捗を報告する日次および週次のレポートを生成するツールセットです。
Windows / Mac の環境差異や文字化けを考慮し、`pathlib` でのパス解決や `utf-8` 指定を徹底しています。

## 構成

- `config.json`: リポジトリと各プロジェクトの対応づけを定義する設定ファイル。
- `scripts/daily_report.py`: 24時間以内の更新を抽出し、リポジトリごとに更新詳細を含めた表形式（Markdown）で日報を作成。
- `scripts/weekly_report.py`: 今週の `target_date` を基準に、「完了予定数」と「遅延数（期限超過かつ未完了）」をリポジトリごとに集計（`--by-label` オプションにも対応）。
- `scripts/dashboard.py`: プロジェクトの全体状況や遅延タスク、アサイン状況などを可視化するモダンなHTMLミニダッシュボードを生成。
- `scripts/utils.py`: 各スクリプトで共通利用する GitHub API 連携や設定ファイル読み取り用のユーティリティ。
- `.github/copilot-instructions.md`: AIエージェントに `/daily`, `/weekly` スラッシュコマンドとして認識させるための指示。

## 設定

このツールセットは複数のリポジトリとプロジェクトを `config.json` で管理します。
プロジェクト開始前にルートディレクトリの `config.json` を編集してください。

**`config.json` の例:**
```json
{
  "projects": [
    {
      "repo": "organization/repoA",
      "owner": "organization",
      "project_number": 1,
      "modes": ["target_date", "sprint"]
    },
    {
      "repo": "your_username/your_repo",
      "owner": "your_username",
      "project_number": 2,
      "modes": ["target_date"]
    }
  ]
}
```
※ `modes` 配列を指定することで、対象プロジェクトを `target_date` モードと `sprint` モードのどちらで集計させるかリポジトリごとに個別に振り分けることができます。

## 事前準備（認証が必要）

GitHub CLI を介して Project データを取得するため、認証が確実に設定されている必要があります。
プログラム内部で `gh auth status` を使って認証チェックを行います。

### 認証方法（どちらかを行ってください）
- **ローカル環境**: コマンドプロンプトやターミナルで `gh auth login` を実行し、ブラウザで認証します。権限が足りない場合は `gh auth refresh -s project` を実行してスコープを追加してください。
- **自動実行環境**: `GH_TOKEN` 環境変数に、必要な権限（`repo`, `read:org`, `project` など）を持ったパーソナルアクセストークン（PAT）を設定します。

## 実行トリガー（3つの方法をサポート）

### 1. 手動でのスクリプト実行

コマンドライン（ターミナル・PowerShell・コマンドプロンプト）から直接実行します。設定は `config.json` から自動で読み込まれます。

```bash
# 日次レポートの作成
python scripts/daily_report.py

# 週次レポートの作成（デフォルト target_date モード）
python scripts/weekly_report.py

# 週次レポートの作成（--mode sprint でスプリント集計モード）
python scripts/weekly_report.py --mode sprint

# HTMLダッシュボードの生成（スプリントモード）
python scripts/dashboard.py --mode sprint
```

生成されたレポートは `reports/daily/` 、 `reports/weekly/` および `reports/dashboard/` 内に保存されます。
（`--mode sprint` を指定した場合は `index_sprint.html` や `_sprint.md` のようにサフィックスが付与されて出力されます）
### 2. AIエージェントからの起動（スラッシュコマンド）

Copilot Chat などのAIアシスタント機能を有しているエディタ（VS Codeなど）で、`.github/copilot-instructions.md` の記述を利用してチャットから実行できます。
- `@workspace /daily 実行して` と指示するとAIが上記コマンドを自動実行します。

### 3. Windowsタスクスケジューラからの定時起動

Windowsタスクスケジューラから毎朝や毎週自動実行させる場合は、以下のようなバッチファイル (`run_daily.bat` など) を用意してタスクを登録してください。
タスクスケジューラは非対話的環境で実行されるため、必ず `GH_TOKEN` を設定し、カレントディレクトリに依存しないように絶対パスを使用するか `cd` を使います。

**バッチファイルの例 (run_daily.bat):**
```bat
@echo off
:: 文字化け防止
chcp 65001 >nul

:: トークン（必須）
set GH_TOKEN=ghp_YourPersonalAccessTokenHere

:: スクリプトが配置されているディレクトリに移動
cd /d "C:\path\to\issue-report"

:: Pythonスクリプトの実行（python のパスが通っていない場合は絶対パスを指定）
python scripts\daily_report.py
```
