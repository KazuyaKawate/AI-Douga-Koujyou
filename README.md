# 🎯 Creator Factory OS — v5.1 — Module SDK Self-Registration Foundation

**v5.1 Phase 2:** **📦 Module SDK 自己登録基盤** — `MODULE_INFO` スキーマ拡張（module_id・entrypoint・status・package_path 等）。`ModuleRegistry.export_registry()` で registry スナップショットを生成。Development Studio に "Module SDK" タブ追加。  
**v5.1 Phase 1:** **✅ Approval Center** — AI CEO・自動化・DevStudio からのアクションをレビューする人間承認ゲートウェイ。自動実行なし。  
**v5.0 Beta Phase 2:** **🧠 AI CEO Core** — OSの全データを横断分析し、健全度・優先度・リスク・機会・推奨アクションを提示するエグゼクティブ決定レイヤー。外部API不使用・自動実行なし・推奨のみ。  
**v5.0 Beta Phase 1:** **🛠️ Development Studio** — ロードマップ・リリース・決定ログ・ミーティングノートを管理するOS開発の司令塔。

**Creator Factory OS** は、ソロクリエイターのための統合型デイリーオペレーティングシステムです。  
毎朝アプリを開くと **Mission Control** が起動し、今日のKPI・タスク・工場状態・財務スナップショットを一画面で確認できます。  
各工場（AI動画工場・note・SNS・営業・会計）へのワンクリックナビゲーションで、作業を即座に開始できます。

> **ベース技術:** Python + Streamlit + OpenAI — ローカルファースト、外部APIは最小限。  
> **前バージョン名:** AI動画工場 (v4.1まで)

---

## スクリーンショット

> _初回ライブセッション後に追加予定_

| ページ | 説明 |
|--------|------|
| ![Mission Control](docs/screenshots/mc_overview.png) | 🎯 Mission Control — 毎日の司令塔 |
| ![KPI Panel](docs/screenshots/mc_kpi.png) | 📊 Today KPI — 実績値をその場で更新 |
| ![Task List](docs/screenshots/mc_tasks.png) | ✅ Today Tasks — チェックボックスで完了管理 |
| ![Factory Cards](docs/screenshots/mc_factories.png) | 🏭 Factory Status — 6工場の稼働状況 |
| ![Dashboard](docs/screenshots/dashboard.png) | 📊 制作ダッシュボード — 動画エピソード進捗 |
| ![AI Studio](docs/screenshots/ai_studio.png) | 🤖 AI Studio — マルチエージェント制作パイプライン |

---

## クイックスタート

| ステップ | 操作 |
|---------|------|
| **Step 1** | デスクトップの `AI動画工場.lnk` をダブルクリック |
| **Step 2** | ターミナルが開きサーバーが起動するまで待つ（初回は 10〜20 秒） |
| **Step 3** | ブラウザが自動で `http://localhost:8501` を開く |
| **Step 4** | サイドバーから **🎯 Mission Control** を選択して今日の作業を開始 |

> ショートカットがない場合は `create_desktop_shortcut.ps1` を右クリック → **PowerShell で実行**  
> 環境確認: `check_environment.bat`  
> 全ユーティリティ: [README_UTILITIES.md](README_UTILITIES.md)

---

## セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/KazuyaKawate/AI-Douga-Koujyou.git
cd AI-Douga-Koujyou
```

### 2. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数を設定

```bash
cp .env.example .env
# .env を編集して OPENAI_API_KEY を設定
```

### 4. プロジェクト整合性チェック（推奨）

```bash
python scripts/check_project.py
```

正常時の出力末尾:

```
STATUS: OK — すべての必須ファイルが揃っています ✅
```

### 5. アプリを起動

```bash
streamlit run app.py
```

`http://localhost:8501` が開きます。サイドバーで **🎯 Mission Control** をクリックして開始。

---

## 主な機能

### 🎯 Mission Control（v4.2 新機能）

毎日の作業司令塔。アプリを開いたらここから始める。

| セクション | 内容 |
|-----------|------|
| **Today KPI** | 7つのKPI指標（売上/note/動画/SNS/営業/開発）を表示・更新 |
| **Today Tasks** | チェックボックス付きタスクリスト。完了で自動保存。▶️ 開始で関連ページへ直接ジャンプ |
| **Factory Status** | 6工場のステータスカード（稼働中/完了数/警告/次のアクション） |
| **Finance Snapshot** | 今日・今月の売上/費用/利益/ROI/損益分岐点 |
| **AI CEO Message** | KPIとタスク状態から今日の優先行動をルールベースで生成（API不要） |
| **Quick Navigation** | 各工場へのワンクリックボタン |
| **Daily Report** | 一日の成果をMarkdown形式でエクスポート (`reports/daily/`) |

### 🎬 AI動画工場（v4.1継続）

| 機能 | 説明 |
|------|------|
| ⚡ 一発生成 | テーマ入力でスクリプト・画像/動画プロンプト・字幕・音声台本を一括生成 |
| 🎞️ エピソード管理 | 生成済みエピソードの閲覧・編集・エクスポート |
| 🧑 キャラクター管理 | キャラクターCRUD・AI生成への自動注入 |
| 🏞️ 背景管理 | ロケーション・カメラ・雰囲気テンプレート |
| 📝 プロンプトビルダー | キャラ×背景×ムード×スタイルを合成してプロンプト生成・保存 |
| 🎭 AI Director | シーン別演出計画（手動 + OpenAI生成） |
| 🎬 制作管理 | 6ステージ制作チェックリスト・書き出しパッケージ |
| 📊 制作ダッシュボード | 全エピソードの進捗一覧・フィルター・ファイルプレビュー |
| 📁 プロジェクト管理 | シリーズ管理・バックアップ・一括操作 |
| 🤖 AI Studio | マルチエージェント制作パイプライン（6エージェント） |

---

## Creator Factory OS — アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│  Streamlit Pages (pages/)                                       │
│  17_Mission_Control  |  8_Dashboard  |  16_AI_Studio  | ...   │
├─────────────────────────────────────────────────────────────────┤
│  HQ Layer — src/hq/                          [v4.2 NEW]        │
│  kpi_manager  |  task_manager  |  factory_status  |  daily_report│
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer — src/agents/                   [v4.1]            │
│  ProducerAgent → DirectorAgent → ScriptAgent                   │
│  → PromptAgent → EditorAgent → PublisherAgent                  │
├─────────────────────────────────────────────────────────────────┤
│  Utils / Managers — src/utils/               [v2.x–v4.x]       │
│  settings  |  character  |  background  |  prompt_builder      │
│  project_manager  |  backup_manager  |  file_manager           │
├─────────────────────────────────────────────────────────────────┤
│  Core Pipeline — src/core/                   [v2.x]            │
│  ai_pipeline  |  episode_manager  |  openai_client             │
│  whisper_client  |  ffmpeg_utils                               │
├─────────────────────────────────────────────────────────────────┤
│  Production Pipeline — src/pipeline/         [v3.x]            │
│  script  |  image  |  video  |  audio  |  export              │
├─────────────────────────────────────────────────────────────────┤
│  Director — src/director/                    [v3.1]            │
│  director_schema  |  director_planner                          │
├─────────────────────────────────────────────────────────────────┤
│  Providers — src/providers/                  [v3.x]            │
│  openai_provider  |  image/video/audio_provider_manual         │
├─────────────────────────────────────────────────────────────────┤
│  Storage: JSON Files + Local Filesystem                        │
│  config/*.json  |  project/EPXX/  |  reports/daily/  |  assets/│
└─────────────────────────────────────────────────────────────────┘
```

### 設計原則

| 原則 | 詳細 |
|------|------|
| **ローカルファースト** | 全データはローカルJSONファイルに保存。クラウドDB不要 |
| **外部API最小化** | OpenAIテキスト生成のみ自動呼び出し。メディア生成は手動（プロバイダー抽象化済み） |
| **ルールベースAI** | AI CEO メッセージなどはAPI不要のルールエンジンで生成 |
| **日次リセット** | KPI実績・タスク状態は毎日ページロード時にリセット |
| **プロバイダー抽象化** | `src/providers/` で生成ロジックを分離。API統合時はここだけ変更 |

---

## フォルダ構成

```
Creator Factory OS (AI動画工場)/
├── app.py                         # Streamlit エントリポイント — v4.2 Creator Factory OS
├── pages/
│   ├── 17_Mission_Control.py      # 🎯 Mission Control（日次司令塔）       [v4.2 NEW]
│   ├── 1_Script.py                # 🎬 台本生成
│   ├── 2_Subtitles.py             # 🔤 字幕生成
│   ├── 3_Assembly.py              # ✂️ 動画組立
│   ├── 4_Files.py                 # 📁 ファイル管理
│   ├── 5_Episode.py               # 🎞️ エピソード管理
│   ├── 6_Produce.py               # ⚡ 一発生成
│   ├── 7_Assets.py                # 📚 素材ライブラリ
│   ├── 8_Dashboard.py             # 📊 制作ダッシュボード（Mission Control統合）
│   ├── 9_Settings.py              # ⚙️ スタジオ設定
│   ├── 10_Characters.py           # 🧑 キャラクター管理
│   ├── 11_Backgrounds.py          # 🏞️ 背景管理
│   ├── 12_Prompt_Builder.py       # 📝 プロンプトビルダー
│   ├── 13_Production.py           # 🎬 制作管理
│   ├── 14_Director.py             # 🎭 AI Director
│   ├── 15_Project_Manager.py      # 📁 プロジェクト管理
│   └── 16_AI_Studio.py            # 🤖 AI Studio
├── src/
│   ├── hq/                        # [v4.2] Mission Control データ層
│   │   ├── kpi_manager.py
│   │   ├── task_manager.py
│   │   ├── factory_status.py
│   │   └── daily_report.py
│   ├── agents/                    # [v4.1] マルチエージェントパイプライン
│   ├── core/                      # AI生成パイプライン（OpenAI）
│   ├── utils/                     # 設定・マネージャー群
│   ├── pipeline/                  # 制作バリデーション
│   ├── director/                  # AI演出計画
│   └── providers/                 # 生成プロバイダー抽象化
├── config/
│   ├── kpi_targets.json           # [v4.2] 日次KPI目標・実績
│   ├── daily_tasks.json           # [v4.2] 日次タスクリスト
│   ├── factory_status.json        # [v4.2] 工場ステータス
│   ├── revenue_expense.json       # [v4.2] 財務データ
│   ├── settings.json              # スタジオ設定
│   ├── characters.json            # キャラクターデータ
│   └── backgrounds.json           # 背景データ
├── reports/
│   └── daily/                     # [v4.2] 日次レポートエクスポート先
├── project/                       # 生成済みエピソード（.gitignore）
├── assets/                        # 素材ライブラリ
├── scripts/
│   └── check_project.py           # プロジェクト整合性チェック
└── docs/
    ├── ARCHITECTURE.md
    ├── USER_GUIDE.md
    └── ROADMAP.md
```

---

## 開発モード / コスト節約モード

| モード | 説明 | 設定場所 |
|--------|------|----------|
| 開発モード | 外部生成API自動呼び出しを無効化 | ⚙️ スタジオ設定 → AI設定 |
| コスト節約モード | OpenAI プロンプトを短縮 | ⚡ 一発生成フォーム内 |

---

## ⚠️ 現在の制限事項

| 項目 | 詳細 |
|------|------|
| メディア自動生成 | 画像・動画・音声の自動生成は非対応。Runway / Nano Banana 等で手動生成 |
| note / SNS / 営業 / 会計工場 | Mission Controlにカードはあるが、ページは未実装（v4.3〜v4.6で順次追加） |
| マルチタブ同時操作 | JSON書き込みはアトミックでない。複数タブの同時操作は非推奨 |
| KPI日次リセット | ページロード時にリセット。日付が変わっても最初のページロードまで前日値が残る |
| OpenAI API | テキスト生成のみ使用。GPT-4o または GPT-4o-mini のAPIキーが必要 |

---

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [ROADMAP.md](ROADMAP.md) | v4.3〜v5.0 の開発計画 |
| [CHANGELOG.md](CHANGELOG.md) | v1.x からの全変更履歴 |
| [RELEASE_NOTES_v4.2.md](RELEASE_NOTES_v4.2.md) | v4.2 詳細リリースノート |
| [RELEASE_NOTES_v4.1.md](RELEASE_NOTES_v4.1.md) | v4.1 詳細リリースノート |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | v2.0〜v3.1 リリースノート |
| [README_UTILITIES.md](README_UTILITIES.md) | Windows ユーティリティスクリプト全リファレンス |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 詳細アーキテクチャ |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | 操作ガイド |

---

## ライセンス

Private project — 社内・個人利用のみ。
