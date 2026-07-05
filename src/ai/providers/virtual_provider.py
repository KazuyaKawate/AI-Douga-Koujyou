"""VirtualAgentProvider — AIOS の「Virtual First」設計原則を実現するローカル AI エンジン.

外部 API を使わず、ルールベース + テンプレートで AI タスクに応答する。
- 開発・テスト時の実 API 代替
- API キーなし・オフラインでも AIOS が稼働できる
- Provider として Router に登録される（Provider 依存なし）

設計原則:
    - Router は VirtualAgentProvider を他の Provider と同じ形で扱う
    - Factory / Kernel は Provider の種類を知らない
    - Virtual → Real へのフォールバックは Router が task_routing で制御する
"""
from __future__ import annotations

import re
import time
from datetime import datetime

from ..task import AITask
from ..response import AIResponse
from .base import BaseProvider


class VirtualAgentProvider(BaseProvider):
    """
    ルールベースのローカル AI エンジン。

    task_type に応じてテンプレート応答を返す。
    実 API が利用不可の場合のフォールバックとして機能する。
    """

    def __init__(self, name: str = "virtual", config: dict | None = None) -> None:
        super().__init__(name, config or {})

    def is_available(self) -> bool:
        return self._config.get("enabled", True)

    def complete(self, task: AITask) -> AIResponse:
        t0 = time.monotonic()
        task_key = task.task_type.value

        try:
            content = self._dispatch(task_key, task.prompt, task)
        except Exception as exc:
            content = f"[VirtualAgent エラー: {exc}]"

        return AIResponse(
            ok=True,
            content=content,
            provider=self.name,
            model="virtual-agent-v1",
            task_type=task_key,
            duration_ms=int((time.monotonic() - t0) * 1000),
            metadata={"stub": True, "virtual": True},
        )

    # ---- Dispatch -------------------------------------------------------

    def _dispatch(self, task_key: str, prompt: str, task: AITask) -> str:
        handlers = {
            "writing":     self._writing,
            "coding":      self._coding,
            "planning":    self._planning,
            "analysis":    self._analysis,
            "review":      self._review,
            "translation": self._translation,
            "default":     self._default,
        }
        handler = handlers.get(task_key, self._default)
        return handler(prompt, task)

    # ---- Task handlers --------------------------------------------------

    def _writing(self, prompt: str, task: AITask) -> str:
        topic = self._extract_field(prompt, "トピック") or self._extract_field(prompt, "topic") or "テーマ"
        tone  = self._extract_field(prompt, "トーン") or "分かりやすく"
        now   = datetime.now().strftime("%Y年%m月%d日")

        # SEO メタ生成リクエストを検出
        if "SEO" in prompt or "メタデータ" in prompt or "json" in prompt.lower():
            return self._seo_meta(topic)

        # ブラッシュアップ / リライトリクエストを検出（"ドラフト" 単体では誤検知するため除外）
        if "リライト" in prompt or "ブラッシュアップ" in prompt:
            return self._polish_article(prompt)

        return f"""# {topic}を徹底解説！今すぐ実践できる完全ガイド

## はじめに

「{topic}」について興味を持っているあなたへ。このガイドでは、初心者でもすぐに実践できる具体的な方法をお伝えします。

## {topic}の基本を理解する

まず、{topic}の基本から押さえましょう。多くの方が最初に躓くポイントは、「どこから始めればよいか分からない」という点です。

### ポイント1: 準備を整える

始める前に必要なものを揃えることが大切です。焦らず一歩ずつ進めていきましょう。

### ポイント2: 小さく始める

完璧を目指すより、まず小さく始めることが成功への近道です。実際に行動することで経験が積まれます。

### ポイント3: 継続する仕組みを作る

継続こそが最大の差別化要因です。毎日少しずつでも続けることが重要です。

## 実践的なステップ

1. **現状を把握する** — まず自分の状況を客観的に見てみましょう
2. **目標を設定する** — 具体的な数値目標を立てることで行動が明確になります
3. **行動計画を作る** — 週単位・月単位の計画を立てましょう
4. **振り返りをする** — 定期的に進捗を確認し、軌道修正します

## よくある失敗と対策

**失敗例**: 計画倒れで続かない
**対策**: まず1週間だけ続けることを目標にする

**失敗例**: 成果が見えなくて諦める
**対策**: 小さな進歩を記録して可視化する

## まとめ

{topic}は、正しい方法で取り組めば誰でも成果を出せます。今日から一歩を踏み出してみてください。

*※ このコンテンツは VirtualAgent によって生成されました（{now}）*
"""

    def _polish_article(self, prompt: str) -> str:
        # プロンプト内のマークダウン本文を抽出（"# " で始まる部分）
        md_match = re.search(r"(#\s+.+)", prompt, re.DOTALL)
        original = md_match.group(1)[:800] if md_match else prompt[:300]
        # 改善した見出しを生成
        title_match = re.search(r"^#\s+(.+)", original, re.MULTILINE)
        title = title_match.group(1) if title_match else "記事"
        return f"""# 【完成版】{title}

{original}

---

## まとめ

本記事では、重要なポイントを分かりやすく解説しました。ぜひ今日から実践してみてください。

*【VirtualAgent ブラッシュアップ済み — 実 AI で更に品質向上できます】*
"""

    def _seo_meta(self, topic: str) -> str:
        return f"""```json
{{
  "title": "{topic}の完全ガイド | 初心者でもわかる実践的な方法",
  "description": "{topic}について徹底解説。初心者でもすぐに実践できる具体的なステップと、よくある失敗を避けるためのコツをご紹介します。",
  "tags": ["{topic}", "入門", "実践ガイド", "ハウツー", "初心者向け"],
  "slug": "complete-guide-{re.sub(chr(32), '-', topic.lower())}"
}}
```"""

    def _coding(self, prompt: str, task: AITask) -> str:
        lang = "Python"
        if "javascript" in prompt.lower() or "js" in prompt.lower():
            lang = "JavaScript"
        elif "typescript" in prompt.lower():
            lang = "TypeScript"
        return f"""```{lang.lower()}
# VirtualAgent によるコードスケルトン
# TODO: 実際の実装が必要です

def placeholder():
    \"\"\"
    リクエスト: {prompt[:100]}...
    実 API (Claude / OpenAI) を使用することで完全な実装が生成されます。
    \"\"\"
    pass
```
*VirtualAgent: 実装プレースホルダーを生成しました。*
"""

    def _planning(self, prompt: str, task: AITask) -> str:
        return f"""# プロジェクト計画書 (VirtualAgent 生成)

## 概要
{prompt[:100]}

## フェーズ計画
1. **フェーズ1 (Week 1-2)**: 調査・要件定義
2. **フェーズ2 (Week 3-4)**: 設計・プロトタイプ
3. **フェーズ3 (Week 5-6)**: 実装
4. **フェーズ4 (Week 7-8)**: テスト・リリース

## リスク
- スコープクリープに注意
- 外部依存関係の確認が必要

*VirtualAgent により生成された計画の骨格です。詳細は実 AI で拡充してください。*
"""

    def _analysis(self, prompt: str, task: AITask) -> str:
        return f"""# 分析レポート (VirtualAgent)

## 分析対象
{prompt[:150]}

## 主要な発見
- 項目A: 検討が必要
- 項目B: 改善余地あり
- 項目C: 良好な状態

## 推奨アクション
1. 優先度高: 早期対応が必要な課題を特定する
2. 優先度中: 中期的な改善を計画する
3. 優先度低: 長期的な最適化を検討する

*詳細な分析には実 AI (Claude / OpenAI) を使用してください。*
"""

    def _review(self, prompt: str, task: AITask) -> str:
        return f"""# レビューレポート (VirtualAgent)

## レビュー結果: 要確認

### 良い点
- 基本構造は適切です
- 主要な要件を満たしています

### 改善点
- さらなる詳細化が必要な箇所があります
- エッジケースへの対応を確認してください

### 総評
概ね良好ですが、実 AI によるより詳細なレビューを推奨します。

*VirtualAgent による初期レビューです。*
"""

    def _translation(self, prompt: str, task: AITask) -> str:
        return f"""[VirtualAgent Translation Stub]

Original:
{prompt[:200]}

Translation: [実 API (OpenAI / Claude) が必要です]

*VirtualAgent は翻訳機能の完全な実装を提供していません。*
"""

    def _default(self, prompt: str, task: AITask) -> str:
        return f"""[VirtualAgent 応答]

リクエスト: {prompt[:200]}

VirtualAgent がリクエストを受け取りました。
実際の AI 処理には OpenAI / Claude API キーの設定が必要です。

現在の設定:
- Virtual モード: 有効
- 実 API: 未設定 (config/workspace_local.json の ai_keys を確認してください)
"""

    # ---- Helpers -------------------------------------------------------

    @staticmethod
    def _extract_field(text: str, field: str) -> str:
        pattern = rf"{field}[：:]\s*(.+?)(?:\n|$)"
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _extract_section(text: str, header: str) -> str:
        idx = text.find(header)
        if idx == -1:
            return ""
        return text[idx + len(header):idx + len(header) + 300].strip()
