# Release Notes — AI動画工場

## v3.1 RC1 (2026-06-26) — First Public Release Candidate

**AI Director Layer**

- 新モジュール `src/director/` を追加
  - `director_schema.py`: 演出計画スキーマ定義・空レコードファクトリー
  - `director_planner.py`: `load/save_director_plan()`, `generate_plan_with_ai()` (OpenAIテキストのみ、画像/動画/音声APIは呼び出さない)
- `pages/14_Director.py`: AI Directorページ
  - 手動モード: 全体トーン・ビジュアルスタイル・ペーシング・シーン別演出を手入力
  - AI生成モード: OpenAIがシーンごとの演出計画JSON（camera_angle/motion/framing/lighting/prompt_direction等）を自動生成
  - エピソード切替時の2パス初期化（session state キーを正しくリセット）
  - `director_plan.json` を `project/EPXX/` に保存
- プロンプトビルダー: 🎬 演出ディレクション セクションを追加。演出計画のシーンをプロンプトに注入可能
- 制作管理: 演出計画ファイルの検証・プレビュー・エクスポートに対応
- ダッシュボード: 🎬 Director バッジ追加
- 一発生成: 生成後に「AI Directorで演出設計」への誘導メッセージ
- `export_pipeline.py`: エクスポートパッケージに `director_plan.json` を追加、`production_report.json` に演出サマリーを追加

---

## v3.0 (2026-06-26) — End-to-End Production Pipeline

**制作パイプライン分離**

- `src/pipeline/` モジュール新設
  - `script_pipeline.py`: 台本ファイルバリデーション
  - `image_pipeline.py`: 画像素材ファイルバリデーション
  - `video_pipeline.py`: 動画クリップバリデーション
  - `audio_pipeline.py`: 音声ファイルバリデーション
  - `export_pipeline.py`: `production_state.json` CRUD、書き出しパッケージ作成
- `src/providers/` モジュール新設 (Manual ベースライン)
  - `openai_provider.py`, `image_provider_manual.py`, `video_provider_manual.py`, `audio_provider_manual.py`
- `pages/13_Production.py`: 制作管理ページ
  - エピソード選択・ファイル検証・6ステージ制作チェックリスト（✅/🔄/⏭/⏸）
  - プロバイダーガイド（プロンプト/字幕プレビュー・ダウンロード）
  - `production_state.json` への進捗保存、書き出しパッケージ作成
- ダッシュボード: 📦 書き出し済 / 🎬 制作可能 バッジ

---

## v2.9 (2026-06-25) — Prompt Builder

- `src/utils/prompt_builder.py`: キャラ×背景×ムード×スタイル×カメラを合成してプロンプト生成
- `pages/12_Prompt_Builder.py`: 4種類の出力タイプ（画像/動画/ボイスディレクション/サムネイル）
- `config/prompt_templates.json`: テンプレートCRUD
- 一発生成・AI パイプラインへのテンプレート注入

---

## v2.8 (2026-06-25) — Background & Scene Manager

- `src/utils/background_manager.py`: 背景CRUD・デフォルト設定・プロンプトスニペット生成
- `pages/11_Backgrounds.py`: 5タブエディタ（基本/ビジュアル/カメラ/プロンプト/アセット）
- `config/backgrounds.json`: ローカルストレージ

---

## v2.7 (2026-06-24) — Character Manager

- `src/utils/character_manager.py`: キャラクターCRUD・デフォルト設定・プロンプトスニペット生成
- `pages/10_Characters.py`: 5タブエディタ（基本情報/外見/性格/プロンプト/アセット）
- `config/characters.json`: ローカルストレージ
- AI パイプラインへのキャラクター注入

---

## v2.6 — Studio Settings

- `pages/9_Settings.py`: スタジオ設定ページ
- AI設定（モデル・コスト節約・開発モード）、生成プロバイダー設定、プロジェクト設定
- `config/settings.json` での永続化

---

## v2.5 — Production Dashboard

- `pages/8_Dashboard.py`: 全エピソードの制作進捗一覧
- ステータス判定・フィルター・ソート・ファイルプレビュー

---

## v2.2 — Asset Library

- `pages/3_Library.py`: 素材ライブラリ管理ページ
- `assets/` フォルダ構造・エピソードへのアサイン

---

## v2.1 — Low-Cost Manual Production

- コスト節約モード（短縮プロンプト）
- 手動制作ガイド（プロンプトコピー → Runway / Nano Banana）

---

## v2.0 — One-Click Generation

- `pages/6_Produce.py`: 一発生成ページ
- OpenAI でスクリプト・シーン分割・画像/動画プロンプト・字幕・音声台本を一括生成
- `src/core/ai_pipeline.py`: AI生成パイプライン

---

## Planned

- v3.2: 動画組立強化（FFmpeg 自動エンコード）
- v3.3: 字幕スタイルエディタ
- v4.0: 外部生成プロバイダー統合（Runway API / ElevenLabs API）
