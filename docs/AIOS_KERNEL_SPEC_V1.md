# AIOS Kernel 仕様書 v1.0

> **Status**: APPROVED — 2026-06-29 正式固定
> このドキュメントは AIOS コアの基準仕様です。今後の Factory・Agent・Workflow の実装はすべてこの仕様に従ってください。

---

## 1. 基本思想

### AIOS とは何か

AIOS は **AI を作るための OS** です。AI チャットアプリではありません。

| 概念 | 役割 | 類似物 |
|------|------|--------|
| AIOS Kernel | すべての中心。依存注入・ライフサイクル管理 | OS Kernel |
| AIRouter | タスクを適切な外部 AI へルーティング | CPU スケジューラ |
| Factory | 業務ドメインの Workflow 定義を提供 | アプリケーション |
| WorkflowRunner | Workflow を実行するエンジン | プロセス実行器 |
| FileMemoryProvider | 永続化されたグローバル記憶 | ファイルシステム |
| 外部 AI (Claude/OpenAI/Gemini) | 計算を実行する処理エンジン | CPU |

### 設計の 3 原則

1. **Virtual First, Real AI Second** — 外部 API がなくても VirtualAgentProvider で全 Workflow が動作する
2. **Factory は Kernel を知らない** — Factory は Workflow 定義を返すだけ。実行責任は Kernel が持つ
3. **Provider 名のハードコード禁止** — どの AI を使うかは Router と `config/ai_router.json` が決める

---

## 2. Kernel の責務

`src/core/kernel.py` の `AIOSKernel` クラスが AIOS 唯一の組み立て点です。

### 起動フロー（順序固定）

```
1. FileMemoryProvider を初期化（data/aios_memory.json から復元）
2. AIRouter を初期化（.env ロード → config/ai_router.json 読み込み）
3. WorkflowRunner を初期化（router + memory を注入）
4. FactoryRegistry.auto_discover() で Factory / Executor / Workflow を全登録
5. FactoryOrchestrator を起動
```

### シングルトン保証

```python
from src.core.kernel import get_kernel
kernel = get_kernel()  # 常に同一インスタンス
```

- `threading.Lock` で二重初期化を防止
- Streamlit の複数セッションでも 1 インスタンスを共有
- テスト・再起動時のみ `reset_kernel()` で破棄可

### Kernel の公開 API

```python
kernel.router          # AIRouter
kernel.memory          # BaseMemoryProvider
kernel.runner          # WorkflowRunner
kernel.orchestrator    # FactoryOrchestrator
kernel.registry        # FactoryRegistry

kernel.run_workflow("writing.article_draft", context={"topic": "..."})
kernel.health()        # 全コンポーネントの健全性 dict
```

### Kernel が知ってよいこと / 知ってはいけないこと

| 知ってよい | 知ってはいけない |
|-----------|----------------|
| コンポーネントの型名 | 特定の Provider 名 ("claude", "openai" 等) |
| 初期化順序 | Factory 内部のビジネスロジック |
| Workflow 名（文字列） | Agent の実装詳細 |

---

## 3. Router 設計

`src/ai/router.py` の `AIRouter` クラス。

### 設定ファイル

`config/ai_router.json` — APIキーは絶対に書かない。

```json
{
  "task_routing": {
    "writing":     ["claude", "openai", "virtual"],
    "coding":      ["claude", "openai", "virtual"],
    "vision":      ["openai", "gemini", "virtual"],
    "translation": ["openai", "claude", "virtual"],
    "default":     ["claude", "openai", "virtual"]
  }
}
```

### Routing ロジック

```
task_type → priority リストを解決
  → 各 provider を順番に試みる:
      1. provider が存在するか
      2. is_available() か（キー有り・enabled=true・パッケージ存在）
      3. supports(task_type) か
      4. complete(task) を実行
      5. ok=True なら採用。ok=False なら次へ
  → 全滅した場合は最後の失敗レスポンスを返す
```

### Provider 優先順位（現在設定）

| タスク | 1st | 2nd | 3rd | 4th |
|--------|-----|-----|-----|-----|
| writing | Claude | OpenAI | — | Virtual |
| coding | Claude | OpenAI | — | Virtual |
| vision | OpenAI | Gemini | — | Virtual |
| translation | OpenAI | Claude | — | Virtual |
| default | Claude | OpenAI | — | Virtual |

Virtual は常に最後のフォールバック。削除禁止。

### Memory への自動記録

ルーティング成功後、Router が自動で以下を Memory に保存:
- `last_provider` — 最後に使ったプロバイダー名
- `last_model` — 最後に使ったモデル名

---

## 4. Memory 設計

`src/ai/memory.py`

### Provider 階層

```
BaseMemoryProvider (ABC)
  ├── FileMemoryProvider    ← 現在使用。data/aios_memory.json に永続化
  ├── NullMemoryProvider    ← テスト用
  └── (将来) GoogleSheetsMemoryProvider, SQLiteMemoryProvider
```

### FileMemoryProvider の動作

- 起動時に `data/aios_memory.json` を読み込み、メモリに展開
- `set()` 呼び出しのたびに即座にファイルへ書き込み（flush）
- キーは `(key, scope)` の複合キー
- バージョン管理: 同一キーへの上書きで `version` を自動インクリメント

### Scope

| Scope | 用途 |
|-------|------|
| GLOBAL | プロジェクト横断の永続情報 |
| PROJECT | 現在プロジェクト内のみ |
| SESSION | 起動中のみ（再起動で消える） |
| USER | マルチユーザー対応向け（将来） |

### TTL

| TTL | 意味 |
|-----|------|
| PERMANENT | 永続 |
| SESSION | セッション終了まで |
| HOURS_24 | 24時間 |
| DAYS_7 | 7日間 |

### 標準キー名 (MemoryKey)

```python
MemoryKey.LAST_PROVIDER        # 最後に使ったプロバイダー
MemoryKey.LAST_MODEL           # 最後に使ったモデル
MemoryKey.CURRENT_PROJECT      # 現在のプロジェクト
MemoryKey.DECISION_HISTORY     # 意思決定履歴
MemoryKey.CONVERSATION_SUMMARY # 会話サマリ
```

---

## 5. Workflow 設計

`src/workflow/`

### 構造

```
WorkflowDefinition
  name: str              "writing.article_draft"
  description: str
  version: str           "1.0.0"
  steps: list[WorkflowStep]
    step_id: str         "draft"
    step_type: StepType  AI_TASK / MEMORY_UPDATE / CONDITION / ...
    depends_on: list     依存ステップ ID
    config: dict         Executor への設定
    retry_max: int       リトライ回数
    on_failure: OnFailure  ABORT / CONTINUE / RETRY
```

### Step 実行順序

- `depends_on` が空のステップは並列実行可（現在は同期実行）
- `depends_on` に指定されたステップが完了するまで待機
- 失敗時は `on_failure` に従い: ABORT（全体停止）/ CONTINUE（スキップ）/ RETRY

### Executor 種別

| StepType | Executor | 用途 |
|----------|----------|------|
| AI_TASK | AITaskExecutor | AI への処理委譲 |
| MEMORY_UPDATE | MemoryUpdateExecutor | Memory への保存 |
| CONDITION | ConditionExecutor | 条件分岐 |
| APPROVAL | ApprovalExecutor | 人間承認待ち |
| SNAPSHOT | SnapshotExecutor | 状態スナップショット |
| INBOX_POLL | InboxPollExecutor | 外部メッセージ取得 |
| QUEUE_PUSH | QueuePushExecutor | キューへの送信 |
| NOTIFICATION | NotificationExecutor | 通知送信 |

### Context の伝搬

```python
# 実行前 context（Workflow 呼び出し時に渡す）
context = {"topic": "AI戦略", "word_count": "800"}

# 各ステップの output_key で context が拡張される
# Step "draft"  → context["draft"]  = "生成された記事..."
# Step "polish" → context["article"] = "ブラッシュアップ後..."
```

---

## 6. Factory 設計

`src/orchestrator/factories/`

### Factory とは

Factory は「Workflow 定義の集合」を提供するクラスです。実行は行いません。

```python
class MyFactory(BaseFactory):
    @property
    def factory_name(self) -> str:
        return "my_factory"         # ← Workflow 名のプレフィックス

    def build_workflow_definitions(self) -> list[WorkflowDefinition]:
        return [self._step_a(), self._step_b()]
```

### Factory 追加時の必須ルール

1. `BaseFactory` を継承する
2. `factory_name` は全 Factory でユニーク
3. Workflow 名は `"{factory_name}.{workflow_name}"` 形式
4. Factory 内で `AIRouter`, `Kernel`, `Provider` を直接呼び出さない
5. AI 処理は必ず `StepType.AI_TASK` の Executor に委譲する
6. `src/orchestrator/factories/` 以下に配置すれば自動発見される（登録不要）
7. `build_workflow_definitions()` を実装する

### 禁止パターン

```python
# NG: Factory 内で直接 AI API を呼ぶ
class BadFactory(BaseFactory):
    def run(self):
        import anthropic
        client = anthropic.Anthropic()  # 絶対禁止
        ...

# NG: Factory 内でプロバイダー名をハードコード
def _build(self):
    config = {"provider": "claude"}    # 絶対禁止 — Router が決める

# NG: Kernel をインポートして使う
from src.core.kernel import get_kernel
kernel = get_kernel()                  # Factory 内での Kernel 直接参照は禁止
```

### 現在登録されている Factory

| Factory | ファイル | Workflow 数 |
|---------|---------|------------|
| WritingFactory | factories/writing.py | 4 |
| CreatorFactory | factories/creator.py | - |
| SNSFactory | factories/sns.py | - |
| VideoFactory | factories/video.py | - |
| MarketingFactory | factories/marketing.py | - |
| ResearchFactory | factories/research.py | - |
| FortuneFactory | factories/fortune.py | - |

---

## 7. Virtual Agent 設計

`src/ai/providers/virtual_provider.py`

### 存在理由

外部 AI API なしで全パイプラインを動作させるための「ローカル AI エミュレーター」。

- API キー不要
- ネット接続不要
- テンプレートベースで確実に動作
- Fallback の最後の砦

### is_available() の特性

```python
def is_available(self) -> bool:
    return self._config.get("enabled", True)
    # キーチェックなし — 常に利用可能
```

### タスク別レスポンス

| task_type | 検出条件 | 出力 |
|-----------|---------|------|
| writing (SEO) | "SEO"/"メタデータ"/"json" を含む | JSON 形式のメタデータ |
| writing (polish) | "リライト"/"ブラッシュアップ" を含む | 構造化されたリライト記事 |
| writing (draft) | 上記以外 | Markdown 形式の記事テンプレート |
| coding | — | コードブロック付きテンプレート |
| planning | — | 計画書テンプレート |
| analysis | — | 分析レポートテンプレート |
| review | — | レビューテンプレート |
| translation | — | 翻訳テンプレート |
| default | — | 汎用テンプレート |

---

## 8. Provider 優先順位とフォールバック設計

### 現在の設定

```
Claude (claude-sonnet-4-6)    ← Primary — 最高品質
  ↓ 失敗時
OpenAI (gpt-4o)              ← Secondary — 汎用
  ↓ 失敗時
Gemini (gemini-2.0-flash-lite)← Tertiary — vision 系に強い（現在クォータ制限中）
  ↓ 失敗時
Virtual (virtual-agent-v1)   ← Last Resort — 常に成功
```

### フォールバック発動条件

- Provider が `is_available() == False`（キー未設定 / enabled=false）
- `complete()` が `ok=False` を返した（API エラー / タイムアウト / クォータ超過）
- Provider がそのタスクタイプに対応していない（`supports() == False`）

### 重要: Virtual は削除禁止

`config/ai_router.json` の各 task_routing リストの末尾 `"virtual"` を削除しないこと。これがなければ API 障害時に全 Workflow が停止する。

---

## 9. API キー管理方針

### 保存場所

| 場所 | 用途 | コミット |
|------|------|---------|
| `.env` | ローカル開発 | 絶対にコミット禁止 |
| `config/workspace_local.json` の `ai_keys` セクション | 代替 | 禁止 |
| 環境変数 | 本番/CI | 推奨 |

### 環境変数名

```
ANTHROPIC_API_KEY   Claude
OPENAI_API_KEY      OpenAI / GPT-4o
GOOGLE_API_KEY      Gemini
```

### `.env` ロードの実装規則

```python
# 正しい実装 — cwd 非依存
from pathlib import Path
from dotenv import load_dotenv
_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=_root / ".env", override=False)

# 禁止 — cwd に依存して失敗する
load_dotenv()
```

### `config/ai_router.json` への記載禁止

`providers` ブロックには `api_key_env`（環境変数名）のみ書く。API キー値は絶対に書かない。

---

## 10. 今後禁止する実装パターン

### Factory 関連

```python
# 禁止 1: Factory 内で外部 AI ライブラリを直接 import
import anthropic, openai, google.genai  # Factory 内では禁止

# 禁止 2: Factory 内でプロバイダーを指定
step_config = {"force_provider": "claude"}  # Router の責務を侵害

# 禁止 3: Factory で Kernel を参照
from src.core.kernel import get_kernel  # Factory が Kernel を知るのは禁止

# 禁止 4: Workflow 名を {factory_name}. プレフィックスなしで付ける
name = "article_draft"  # NG: "writing.article_draft" が正しい
```

### Kernel 関連

```python
# 禁止 5: Kernel の外でプロバイダーを直接インスタンス化
from src.ai.providers.claude_provider import ClaudeProvider
p = ClaudeProvider(...)  # Factory / Workflow コードでは禁止（テストを除く）

# 禁止 6: reset_kernel() を本番コードで呼ぶ
reset_kernel()  # テスト専用
```

### Memory 関連

```python
# 禁止 7: .env から API キーを Memory に保存する
memory.set("api_key", os.environ["ANTHROPIC_API_KEY"])  # 絶対禁止

# 禁止 8: 存在しないメソッドを呼ぶ
memory.save(...)   # 存在しない → memory.set() を使う
memory.store(...)  # 存在しない
```

---

## 11. ファイル配置規則

```
AI動画工場/
├── src/
│   ├── core/kernel.py          ← Kernel（変更頻度: 極低）
│   ├── ai/
│   │   ├── router.py           ← Router（変更頻度: 低）
│   │   ├── memory.py           ← Memory インターフェース（変更頻度: 低）
│   │   └── providers/          ← AI プロバイダー実装（追加は可）
│   ├── workflow/
│   │   ├── runner.py           ← Workflow 実行（変更頻度: 低）
│   │   ├── models.py           ← WorkflowDefinition, WorkflowStep
│   │   └── executors/          ← Executor 実装（追加は可）
│   └── orchestrator/
│       └── factories/          ← Factory 実装（追加は可・自動発見）
├── config/
│   └── ai_router.json          ← Router 設定（キー値禁止）
├── data/
│   └── aios_memory.json        ← 永続化 Memory（git commit 禁止）
└── .env                        ← API キー（git commit 絶対禁止）
```
