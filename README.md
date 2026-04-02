# issue-report
Create Daily Report and Weekly Report from GitHub issues.

---
## **GitHub Issue/Project 報告ツール実装要件**

### **1. システム構成と依存関係**
* **実行環境:** Python 3.10+ (macOS / Windows 11 両対応)
* **認証・データ取得:** GitHub CLI (`gh`) をラッパーとして使用。
    * `gh project item-list` コマンドまたは GraphQL API を使用して、Project内のカスタムフィールド（`target_date`）を取得すること。
* **ファイル操作:** * `pathlib` モジュールを使用し、OS固有のパス問題を回避。
    * 全出力ファイルは `utf-8` エンコーディングで保存。

### **2. `daily_report.py` (日次レポート) 仕様**
* **入力:** プロジェクトID、リポジトリ名。
* **抽出対象:** 直近24時間以内に更新があったIssue。
* **必須表示項目:** * Issue番号 / タイトル
    * ステータス
    * **Assignees (担当者名)**
    * `target_date` (Projectフィールド値)
* **ロジック:** 担当者ごとにグループ化し、Markdown形式で `reports/daily/YYYY-MM-DD.md` に保存。

### **3. `weekly_report.py` (週次レポート) 仕様**
* **入力:** プロジェクトID、リポジトリ名。
* **抽出対象:** 指定した週（月〜日）の範囲に `target_date` が含まれるIssue。
* **必須表示項目:**
    * **完了予定Issue数:** `target_date` が今週の範囲内にある総数。
    * **遅延Issue数:** `target_date` が本日以前であり、かつステータスが「完了（Done/Closed）」以外。
    * 主要なトピックの要約（ステータスが更新されたもの）。
* **制約:** **Assigneesは表示しない。**
* **出力:** `reports/weekly/YYYY-MM-W(週番号).md` に保存。

### **4. スラッシュコマンド・インターフェース要件**
以下の定義を含む `.github/copilot-instructions.md` を作成すること。

* **`/daily`**: 
    1. `python scripts/daily_report.py` を実行。
    2. 生成されたMarkdownの内容をVS Code Chat内にプレビュー表示。
* **`/weekly`**: 
    1. `python scripts/weekly_report.py` を実行。
    2. 週次サマリをChat内に表示し、上長報告用のテキストとして整形。
