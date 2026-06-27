# アーキテクチャ — Creator Factory OS v4.7

## 概要

Creator Factory OS はローカルファースト・JSONファースト設計の Streamlit マルチページアプリです。  
v4.4 で **SNS Factory (`src/factories/sns/`)** を追加し、7プラットフォーム対応のSNS投稿管理工場が稼働しました。  
v4.3 で **Note Factory (`src/factories/note/`)** を追加。v4.2 で **HQ Layer (`src/hq/`)** を追加し、Mission Control の日次オペレーションを支えるデータ層を分離しました。  
外部APIはOpenAIテキスト生成のみ。AI CEOメッセージなどはAPIを呼ばないルールエンジンで生成します。

---

## レイヤー構成

```
┌─────────────────────────────────────────────────────────────────┐
│  Streamlit Pages (pages/)                                       │
│  17_Mission_Control  |  8_Dashboard  |  16_AI_Studio  | ...   │
│  ユーザーインターフェース層                                       │
├─────────────────────────────────────────────────────────────────┤
│  HQ Layer — src/hq/                             [v4.2 NEW]     │
│  kpi_manager  |  task_manager                                   │
│  factory_status  |  daily_report                                │
│  Mission Control の日次データ管理                                │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer — src/agents/                      [v4.1]         │
│  ProducerAgent → DirectorAgent → ScriptAgent                   │
│  → PromptAgent → EditorAgent → PublisherAgent                  │
│  TaskQueue (file-backed JSON)  |  AgentRegistry                │
├─────────────────────────────────────────────────────────────────┤
│  Utils / Managers — src/utils/                  [v2.x–v4.x]    │
│  settings_manager  |  character_manager  |  background_manager │
│  prompt_builder  |  project_manager  |  backup_manager         │
│  file_manager  |  config                                        │
├─────────────────────────────────────────────────────────────────┤
│  Core Pipeline — src/core/                      [v2.x]         │
│  ai_pipeline  |  episode_manager                                │
│  openai_client  |  whisper_client  |  ffmpeg_utils             │
├─────────────────────────────────────────────────────────────────┤
│  Production Pipeline — src/pipeline/            [v3.x]         │
│  script_pipeline  |  image_pipeline  |  video_pipeline         │
│  audio_pipeline  |  export_pipeline                            │
├─────────────────────────────────────────────────────────────────┤
│  Director — src/director/                       [v3.1]         │
│  director_schema  |  director_planner                          │
├─────────────────────────────────────────────────────────────────┤
│  Providers — src/providers/                     [v3.x]         │
│  openai_provider  |  image/video/audio_provider_manual         │
│  （将来: runway / elevenlabs プロバイダー追加予定）             │
├─────────────────────────────────────────────────────────────────┤
│  Storage: JSON Files + Local Filesystem                        │
│  config/*.json  |  project/EPXX/  |  reports/daily/  |  assets/│
└─────────────────────────────────────────────────────────────────┘
```

---

## ページ構成 (v4.2)

| ページ | ファイル | 主な役割 | バージョン |
|--------|---------|---------|-----------|
| 🎯 Mission Control | `17_Mission_Control.py` | 日次KPI・タスク・工場状態・財務・AI CEO | v4.2 |
| 🎬 台本生成 | `1_Script.py` | 台本・プロンプト生成 | v1.x |
| 🔤 字幕生成 | `2_Subtitles.py` | Whisper字幕生成 | v1.x |
| ✂️ 動画組立 | `3_Assembly.py` | FFmpeg組立 | v1.x |
| 📁 ファイル管理 | `4_Files.py` | プロジェクトファイル一覧 | v1.x |
| 🎞️ エピソード管理 | `5_Episode.py` | エピソードCRUD | v2.x |
| ⚡ 一発生成 | `6_Produce.py` | AI生成フォーム・結果表示 | v2.0 |
| 📚 素材ライブラリ | `7_Assets.py` | 素材管理・アサイン | v2.2 |
| 📊 ダッシュボード | `8_Dashboard.py` | 進捗一覧 + Mission Controlサマリー | v2.5 / v4.2 |
| ⚙️ スタジオ設定 | `9_Settings.py` | 設定CRUD | v2.6 |
| 🧑 キャラクター | `10_Characters.py` | キャラクターCRUD | v2.7 |
| 🏞️ 背景 | `11_Backgrounds.py` | 背景CRUD | v2.8 |
| 📝 プロンプトビルダー | `12_Prompt_Builder.py` | プロンプト生成・テンプレート | v2.9 |
| 🎬 制作管理 | `13_Production.py` | チェックリスト・エクスポート | v3.0 |
| 🎭 AI Director | `14_Director.py` | 演出計画設計 | v3.1 |
| 📁 プロジェクト管理 | `15_Project_Manager.py` | シリーズ・バックアップ・一括操作 | v4.1 |
| 🤖 AI Studio | `16_AI_Studio.py` | マルチエージェントパイプライン | v4.1 |

---

## データフロー

### Mission Control 日次フロー (v4.2)

```
アプリ起動
  ↓
pages/17_Mission_Control.py
  ↓ load_kpi()            ← src/hq/kpi_manager.py
  ↓ load_tasks()          ← src/hq/task_manager.py
  ↓ load_factory_status() ← src/hq/factory_status.py
  ↓ sync_from_tasks()     ← factory counts ← task statuses
  ↓ config/revenue_expense.json
  ↓
表示: KPI metrics | Task checkboxes | Factory cards | Finance
  ↓
ユーザーアクション:
  ├── Checkbox toggle → update_task_status() → config/daily_tasks.json
  ├── KPI number input → update_actual() → config/kpi_targets.json
  ├── Finance save → config/revenue_expense.json
  ├── ▶️ 開始 → in_progress + st.page_link()
  └── Export → generate_report() → reports/daily/YYYY-MM-DD_daily_report.md
```

### 一発生成フロー (v2.0〜)

```
ユーザー入力 (topic, episode_id, duration, ...)
  ↓
pages/6_Produce.py
  ↓ character/background/template オプション注入
src/core/ai_pipeline.generate_episode_ai()
  ↓ OpenAI Chat Completions API (テキストのみ)
JSON パース → episode.json 書き出し
  + *_image_prompts.txt / *_video_prompts.txt
  + *_voice_script.txt / *.srt
  ↓
project/EPXX/
```

### マルチエージェントパイプライン (v4.1〜)

```
pages/16_AI_Studio.py
  ↓ AgentRegistry.run_task()
ProducerAgent → DirectorAgent → ScriptAgent
  → PromptAgent → EditorAgent → PublisherAgent
  ↓ 各エージェント: Task オブジェクト (project/tasks/*.json)
  ↓ OpenAI API (Producer / Director のみ)
出力: episode.json + director_plan.json + export package
```

---

## ストレージ設計 (v4.2)

| ファイル | 場所 | 用途 | リセット |
|---------|------|------|---------|
| `kpi_targets.json` | `config/` | 日次KPI目標・実績 | 毎日（実績のみ） |
| `daily_tasks.json` | `config/` | 日次タスクリスト | 毎日（未完了タスクをpendingに） |
| `factory_status.json` | `config/` | 工場ステータスカード | ページロード時にタスクから同期 |
| `revenue_expense.json` | `config/` | 財務データ | 手動更新 |
| `settings.json` | `config/` | アプリ全体設定 | 手動更新 |
| `characters.json` | `config/` | キャラクターCRUD | 手動更新 |
| `backgrounds.json` | `config/` | 背景CRUD | 手動更新 |
| `prompt_templates.json` | `config/` | プロンプトテンプレート | 手動更新 |
| `agent_registry.json` | `config/` | エージェント設定 | 手動更新 |
| `episode.json` | `project/EPXX/` | エピソードデータ | — |
| `director_plan.json` | `project/EPXX/` | 演出計画 | — |
| `production_state.json` | `project/EPXX/` | 制作進捗チェックリスト | — |
| `production_report.json` | `project/EPXX/export/` | エクスポートサマリー | — |
| `task_*.json` | `project/tasks/` | エージェントタスク | TaskQueue管理 |
| `YYYY-MM-DD_daily_report.md` | `reports/daily/` | 日次レポートエクスポート | 手動管理 |

---

## 設計原則

| 原則 | 詳細 |
|------|------|
| **ローカルファースト** | 全データはローカルファイルシステム。クラウドDB不要 |
| **JSONファースト** | スキーマは柔軟なJSON。マイグレーション不要。`read_text(encoding="utf-8")` / `write_text(encoding="utf-8")` 統一 |
| **外部API最小化** | OpenAIテキスト生成のみ自動呼び出し。AIメッセージ生成はAPIゼロのルールエンジン |
| **プロバイダー抽象化** | `src/providers/` で生成ロジックを分離。将来のRunway/ElevenLabs追加時はここだけ変更 |
| **パイプライン分離** | `src/pipeline/` でバリデーションロジックをUIから分離 |
| **Lazy imports** | 循環インポートを避けるため、`_call_openai()` 内でマネージャーを遅延インポート |
| **日次リセット** | KPI実績・タスク状態は `date` フィールドで日付変化を検出し自動リセット |

---

## Session State パターン

| ページ | パターン |
|--------|---------|
| Mission Control タスク | `on_change=_task_on_change, args=(task_id,)` コールバック → JSON保存 → `st.rerun()` |
| Mission Control タスク開始 | `st.session_state[f"show_link_{tid}"]` で 開始後リンクを維持表示 |
| キャラクター/背景エディタ | `key=f"{record_id}_fieldname"` でレコード切替時にウィジェットをリセット |
| プロンプトビルダー | `pb_load_id` シグナルでテンプレートをロード → `st.rerun()` |
| AI Director | `dir_last_ep_id` でエピソード切替を検出し、2パス初期化 → `st.rerun()` |
| AI Studio | `ai_studio_registry` / `ai_studio_queue` でセッション内シングルトン管理 |

---

## v4.3 以降の拡張ポイント

| 機能 | 拡張方法 |
|------|---------|
| Note Factory | `src/factories/note/` を追加。`src/hq/task_manager.py` の `CATEGORIES` に自動対応 |
| 工場間連携 | `config/factory_events.json` にイベントログを追加。各工場のマネージャーがイベントを発行 |
| KPI自動更新 | 工場マネージャーが完了時に `update_actual()` を呼ぶだけ |
| SQLite移行 | `task_manager.py` / `kpi_manager.py` の `_save()` / `load_*()` だけ差し替え |
