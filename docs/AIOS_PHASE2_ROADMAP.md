# AIOS Phase 2 開発ロードマップ

> **基準日**: 2026-06-29
> Phase 1 (AIOS Core) 完了を受けて、次フェーズの実装優先順位を定義します。

---

## Phase 1 完了済み（ベースライン）

- [x] AIOS Kernel — シングルトン・依存注入・起動フロー
- [x] AIRouter — タスク別優先順位ルーティング + フォールバック
- [x] FileMemoryProvider — JSON 永続化メモリ
- [x] WorkflowRunner — ステップ依存解決・同期実行
- [x] WritingFactory — article_draft / article_polish / article_full / seo_meta
- [x] VirtualAgentProvider — API なしでの完全動作
- [x] Claude / OpenAI / Gemini Provider 実装
- [x] 三段フォールバック確認（Claude → OpenAI → Virtual）

---

## Phase 2 実装計画

### Priority 1: Agent Builder

**目標**: AIOS 上で動作するカスタム Agent を GUI から作成・登録できるようにする

**実装内容**:
- `AgentDefinition` モデル（name, role, capabilities, routing_hint, memory_scope）
- `AgentRegistry` — 登録・検索・CRUD
- `AgentBuilder` UI ページ（Streamlit）
- Agent を Workflow の `ai_task` ステップから呼び出せる連携

**完了条件**: Agent を GUI で作成し、Workflow から名前指定で呼び出せること

**依存関係**: Phase 1 完了（済）

**見積もり**: 3〜5日

---

### Priority 2: Virtual Claude Code 完成

**目標**: AIOS 内でコード生成・レビュー・デバッグを Claude に依頼できる内部ツール

**実装内容**:
- `CodeFactory` — code_generate / code_review / code_debug Workflow
- コード生成プロンプトテンプレート
- 生成コードの差分表示・承認フロー（ApprovalExecutor 活用）
- `src/orchestrator/factories/code.py`

**完了条件**: 「この関数を書いて」→ Claude が生成 → 差分確認 → ファイルに書き込み

**依存関係**: Priority 1 (Agent Builder) 完了推奨

**見積もり**: 5〜7日

---

### Priority 3: Google Sheets 連携完成

**目標**: AIOS の Memory と Google Sheets を双方向同期する

**実装内容**:
- `GoogleSheetsMemoryProvider` — `BaseMemoryProvider` 実装
- `SheetsWorkflowExecutor` — Sheets への読み書き Executor
- `gspread` 認証フロー（Service Account）
- `WorkspaceFactory` — sync_to_sheets / sync_from_sheets Workflow
- Kernel の `_init_memory()` で `GOOGLE_SHEETS_ID` が設定されていれば Sheets Provider に切り替え

**完了条件**: `memory.set("key", "value")` の結果が自動的に Google Sheets に反映される

**依存関係**: Phase 1 完了（済）、Google Cloud 課金設定（Gemini クォータと共通）

**見積もり**: 5〜7日

---

### Priority 4: Factory Plugin System

**目標**: Factory を ZIP/フォルダ単位で配布・インストールできるプラグインシステム

**実装内容**:
- `FactoryManifest` — name, version, author, workflows, dependencies を記述する YAML
- `FactoryInstaller` — manifest 検証 → ファイルコピー → Registry 再ロード
- SDK: `src/sdk/` 以下のモジュールローダー活用
- `plugin install <path>` CLI コマンド

**完了条件**: ZIP を渡すだけで新 Factory が AIOS に追加される

**依存関係**: Priority 1, 2 完了推奨

**見積もり**: 7〜10日

---

### Priority 5: Event Bus

**目標**: Factory・Workflow・Agent 間の非同期イベント通信基盤

**実装内容**:
- `EventBus` — パブリッシュ/サブスクライブ（インプロセス）
- `EventType` 列挙（WORKFLOW_COMPLETED, MEMORY_UPDATED, AGENT_STARTED, ...）
- `EventBusExecutor` — StepType.EMIT_EVENT として Workflow から発火
- Kernel への統合（`kernel.event_bus`）

**完了条件**: `writing.article_full` 完了 → `SNSFactory` が自動起動する連携が動作する

**依存関係**: Priority 1〜3 完了推奨

**見積もり**: 5〜7日

---

### Priority 6: Learning Engine

**目標**: 過去の Workflow 実行履歴から AIOS が自己改善できる仕組み

**実装内容**:
- `WorkflowMetrics` — 各実行の品質スコア・所要時間・コストを記録
- `ProviderPerformanceTracker` — Provider 別の成功率・レイテンシ・コスト集計
- Router への品質フィードバック — 低品質プロバイダーの優先度を動的に下げる
- `LearningReport` — 週次レポート Workflow

**完了条件**: Claude の応答品質が低下したとき、自動的に OpenAI へ優先度を切り替える

**依存関係**: Priority 5 (Event Bus) 完了推奨

**見積もり**: 10〜14日

---

### Priority 7: AI Company Engine

**目標**: AIOS が複数 Factory を協調させて「1つの会社」として動作する

**実装内容**:
- `CompanyOrchestrator` — 複数 Factory を横断するメタ Orchestrator
- `DailyPlan` Workflow — AI CEO が当日の Factory 稼働計画を立案
- `CrossFactoryWorkflow` — Writing → SNS → Sales の連鎖実行
- KPI 自動追跡・ダッシュボード更新

**完了条件**: 「今日の記事を書いて SNS に投稿し売上を計上する」を 1 コマンドで実行できる

**依存関係**: Priority 5, 6 完了推奨

**見積もり**: 14〜21日

---

### Priority 8: Marketplace 構想

**目標**: Factory / Workflow / Agent をマーケットプレイスで配布・販売できるエコシステム

**実装内容**:
- Factory カタログ API
- ライセンス管理
- 収益分配モデル
- Factory レビュー・品質スコア
- AIOS Hub（Web ポータル）

**前提条件**: Priority 4 (Plugin System) 完了必須

**見積もり**: 企画フェーズ含め 1〜3ヶ月

---

## 実装優先マトリクス

```
インパクト
  高 │ [P3] Google Sheets     [P7] AI Company Engine
     │ [P1] Agent Builder     [P6] Learning Engine
     │
  低 │ [P2] Virtual Claude    [P5] Event Bus
     │ Code                   [P4] Factory Plugin
     └──────────────────────────────────────────
       実装コスト 低                     高
```

## 次の 2 週間のスプリント計画

| 週 | タスク |
|----|--------|
| Week 1 | Agent Builder 設計 + AgentDefinition モデル実装 |
| Week 2 | Google Sheets 連携 + GoogleSheetsMemoryProvider |

---

## 設計制約（変更不可）

これらは Phase 2 以降も維持する:

1. **Kernel は Factory を知らない** — auto_discover で動的登録のみ
2. **Factory は AI を知らない** — Router 経由のみ
3. **Virtual は常に存在する** — 最後のフォールバックとして削除禁止
4. **Memory は差し替え可能** — Provider インターフェースを守る限り実装を変えてよい
5. **Workflow 名前空間** — `{factory_name}.{workflow_name}` 形式を維持
