# アーキテクチャ — AI動画工場

## 概要

AI動画工場はローカルファースト・JSONファースト設計の Streamlit マルチページアプリです。
外部APIはOpenAIテキスト生成のみ。画像・動画・音声は手動ツールに委ねます。

---

## レイヤー構成

```
┌─────────────────────────────────────────────┐
│  Streamlit Pages (pages/)                   │
│  ユーザーインターフェース層                  │
├─────────────────────────────────────────────┤
│  Utils / Managers (src/utils/)              │
│  データCRUD・プロンプト生成ロジック           │
├─────────────────────────────────────────────┤
│  Core Pipeline (src/core/)                  │
│  AI生成パイプライン (OpenAI のみ)             │
├─────────────────────────────────────────────┤
│  Production Pipeline (src/pipeline/)        │
│  ファイルバリデーション・制作状態管理         │
├─────────────────────────────────────────────┤
│  Director (src/director/)                   │
│  演出計画生成・管理                          │
├─────────────────────────────────────────────┤
│  Providers (src/providers/)                 │
│  生成プロバイダー抽象化 (現在は Manual のみ)  │
├─────────────────────────────────────────────┤
│  Storage: JSON Files + Local Filesystem     │
│  config/*.json, project/EPXX/, assets/      │
└─────────────────────────────────────────────┘
```

---

## ページ構成

| ページ | ファイル | 主な役割 |
|--------|---------|---------|
| ホーム | `app.py` | フローメトリクス・クイックスタート |
| ⚡ 一発生成 | `6_Produce.py` | AI生成フォーム・結果表示 |
| 🎞️ エピソード管理 | `7_Episodes.py` | エピソードCRUD |
| 📊 ダッシュボード | `8_Dashboard.py` | 進捗一覧・バッジ |
| ⚙️ スタジオ設定 | `9_Settings.py` | 設定CRUD |
| 🧑 キャラクター | `10_Characters.py` | キャラクターCRUD |
| 🏞️ 背景 | `11_Backgrounds.py` | 背景CRUD |
| 📝 プロンプトビルダー | `12_Prompt_Builder.py` | プロンプト生成・テンプレート |
| 🎬 制作管理 | `13_Production.py` | チェックリスト・エクスポート |
| 🎭 AI Director | `14_Director.py` | 演出計画設計 |

---

## データフロー

### 一発生成フロー

```
ユーザー入力 (topic, episode_id, ...)
  ↓
pages/6_Produce.py
  ↓ character / background / template オプション
src/core/ai_pipeline.generate_episode_ai()
  ↓
src/core/ai_pipeline._call_openai()
  ├── character_to_prompt_snippet()    ← src/utils/character_manager
  ├── background_to_prompt_snippet()  ← src/utils/background_manager
  └── template_to_pipeline_note()     ← src/utils/prompt_builder
  ↓ OpenAI Chat Completions API
JSON パース → episode.json 書き出し
  + *_image_prompts.txt
  + *_video_prompts.txt
  + *_voice_script.txt
  + *.srt
  ↓
project/EPXX/
```

### 制作管理フロー

```
project/EPXX/episode.json
  ↓
src/pipeline/script_pipeline.validate_script()
src/pipeline/image_pipeline.validate_images()
src/pipeline/video_pipeline.validate_videos()
src/pipeline/audio_pipeline.validate_audio()
  ↓
src/pipeline/export_pipeline.create_export_package()
  ├── director_plan.json (from src/director/)
  └── production_report.json
  ↓
project/EPXX/export/
```

### AI Director フロー

```
pages/14_Director.py
  ↓ (AI生成モード)
src/director/director_planner.generate_plan_with_ai()
  ↓ OpenAI Chat Completions (テキストのみ)
JSON パース → schema バリデーション
  ↓ session state 経由
_init_plan_state() → widget keys 更新 → st.rerun()
  ↓ (保存)
_collect_plan() → save_director_plan()
  ↓
project/EPXX/director_plan.json
```

---

## ストレージ設計

| ファイル | 場所 | 用途 |
|---------|------|------|
| `settings.json` | `config/` | アプリ全体設定 |
| `characters.json` | `config/` | キャラクターCRUD |
| `backgrounds.json` | `config/` | 背景CRUD |
| `prompt_templates.json` | `config/` | プロンプトテンプレート |
| `episode.json` | `project/EPXX/` | エピソードデータ |
| `director_plan.json` | `project/EPXX/` | 演出計画 |
| `production_state.json` | `project/EPXX/` | 制作進捗 |
| `production_report.json` | `project/EPXX/export/` | エクスポートレポート |

---

## 設計原則

1. **ローカルファースト**: 全データはローカルファイルシステムに保存。クラウドDB不要。
2. **JSONファースト**: スキーマは柔軟なJSON。マイグレーション不要。
3. **外部API最小化**: OpenAIテキスト生成のみ自動呼び出し。画像/動画/音声は手動。
4. **プロバイダー抽象化**: `src/providers/` で生成ロジックを分離。将来のAPI統合を容易にする。
5. **パイプライン分離**: `src/pipeline/` でバリデーションロジックをUIから分離。
6. **Lazy imports**: 循環インポートを避けるため、`_call_openai()` 内でマネージャーを遅延インポート。

---

## Session State パターン

- **キャラクター/背景エディタ**: `key=f"{record_id}_fieldname"` でレコード切替時にウィジェットをリセット
- **プロンプトビルダー**: `pb_load_id` シグナルでテンプレートをロード（`st.session_state` → `st.rerun()`）
- **AI Director**: `dir_last_ep_id` でエピソード切替を検出し、2パス初期化（`_init_plan_state()` + `st.rerun()`）
