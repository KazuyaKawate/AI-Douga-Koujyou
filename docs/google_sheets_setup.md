# Google Sheets セットアップガイド — Creator Factory OS v5.2 Phase 4-2

> **重要:** このガイドはオプション設定です。  
> `auth_mode` のデフォルトは `"disabled"` のまま維持されます。  
> 実際のGoogle Sheets接続は完全に任意であり、設定しなくてもOSのすべての機能は動作します。

---

## セキュリティ原則

**認証情報（credentials）は絶対にリポジトリにコミットしないでください。**

- `credentials/` フォルダは `.gitignore` で除外されています（`.gitkeep` のみ追跡）
- サービスアカウントJSONファイル、OAuthクライアントJSONはローカルのみに配置
- `config/workspace_settings.json` には**ファイルパスのみ**を記録し、実際の認証情報は含めない
- `token.json` も `.gitignore` で除外されています

---

## Phase 4-1: 読み取り専用接続（現フェーズ）

**Phase 4-1** から、サービスアカウントを使った **Google Sheets への読み取り接続** が可能になりました。

| フェーズ | 機能 | 状態 |
|---------|------|------|
| Phase 3 | 安全性確認・依存パッケージチェック | ✅ 完了 |
| Phase 4-1 | gspread 接続コード実装（build_client / read_sheet / test_read_connection） | ✅ 完了 |
| **Phase 4-2** | **ローカル設定上書き（workspace_local.json）& 読み取り接続テスト** | ✅ 現フェーズ |
| Phase 4-3 | 書き込み有効化（`allow_write=True`） | 🔲 予定 |
| Phase 4-4 | OAuth 認証 | 🔲 予定 |

---

## 前提パッケージ（Phase 4-1 接続に必要）

Google Sheets 読み取りには以下のパッケージが必要です。インストールしない場合は `auth_mode=disabled` のままドライランモードで動作します。

```bash
pip install gspread google-auth
```

インストール後、Development Studio → Workspace Sync タブで依存パッケージのステータスが ✅ に更新されます。

> **注意:** `auth_mode=disabled` のままであれば、これらのパッケージなしですべての機能が動作します。

---

## Step 1: Google Cloud プロジェクトのセットアップ

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. **APIs & Services → Enable APIs** を開く
4. **Google Sheets API** を検索して有効化
5. **Google Drive API** も有効化（スプレッドシートへのアクセスに必要）

---

## Step 2: サービスアカウントの作成（推奨方法）

1. **APIs & Services → Credentials** を開く
2. **Create Credentials → Service Account** をクリック
3. サービスアカウント名を入力（例: `creator-factory-sync`）
4. ロールは **Editor** または **Viewer** を付与（Phase 4-1 は読み取りのみ = Viewer で十分）
5. 作成後、サービスアカウントをクリック → **Keys タブ** → **Add Key → JSON**
6. ダウンロードされたJSONファイルを **必ず** 以下のパスに配置:
   ```
   credentials/service-account.local.json
   ```
   ※ `.gitignore` に `credentials/` および `credentials/service-account.local.json` が明示的に追加されているためコミットされません  
   ※ `git status` で表示されないことを必ず確認してください

---

## Step 3: スプレッドシートの共有設定

1. Google Driveで同期対象のスプレッドシートを開く
2. 右上の **共有** ボタンをクリック
3. サービスアカウントのメールアドレスを追加（JSONファイル内の `client_email` フィールド）
4. 権限を **編集者** に設定
5. スプレッドシートのURLからIDをコピー:
   ```
   https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit
   ```

---

## Step 4: config/workspace_local.json の作成（Phase 4-2 NEW）

**`config/workspace_settings.json` は変更しないでください。** `auth_mode=disabled` がリポジトリ上の安全なデフォルトです。

代わりに **ローカル専用の上書きファイル** `config/workspace_local.json` を作成します:

```json
{
  "_comment": "LOCAL-ONLY. DO NOT COMMIT. See docs/google_sheets_setup.md.",
  "auth_mode": "service_account",
  "service_account_file": "credentials/service-account.local.json",
  "spreadsheet_id": "YOUR_SPREADSHEET_ID_HERE",
  "worksheet_name": "KPI",
  "range": ""
}
```

**設定値:**
- `auth_mode`: `"service_account"` に変更（ローカルのみ）
- `service_account_file`: サービスアカウントJSONのパス（`credentials/service-account.local.json`）
- `spreadsheet_id`: Google SheetsのURLから取得（`https://docs.google.com/spreadsheets/d/[ここ]/edit`）
- `worksheet_name`: 読み取るシート名（例: `"KPI"`, `"Sheet1"`）

> **このファイルは `.gitignore` に登録されており、コミットされません。** `auth_mode` や `spreadsheet_id` はこのファイルにのみ設定してください。

---

## Step 5: 読み取り接続テスト (Phase 4-2)

1. `pip install gspread google-auth` を実行（未インストールの場合）
2. `credentials/service-account.local.json` を配置（Step 3）
3. `config/workspace_local.json` を作成・設定（Step 4）
4. Streamlit アプリを起動: `streamlit run Home.py`
5. **Development Studio → Tab 10 (Workspace Sync)** を開く
6. **Phase 4-2: ローカル設定 & 読み取り接続テスト** セクションで以下を確認:

| チェック項目 | 期待値 |
|-------------|--------|
| `config/workspace_local.json` | ✅ 存在 |
| 📦 gspread | ✅ バージョン表示 |
| 📦 google-auth | ✅ バージョン表示 |
| 🔑 auth_mode (実効値) | `service_account` |
| 📄 認証ファイル | ✅ 存在 |
| 🆔 spreadsheet_id | ✅ 設定済み |
| 📋 worksheet_name | シート名表示 |

7. **「🔌 読み取り接続テスト」** ボタンをクリック
8. 成功: `✅ 接続テスト成功 | ソース: ライブ読み取り | 行数: XX | 〇ms`

> **書き込みは Phase 4-3 まで無効。** Phase 4-2 は読み取り専用です。`allow_write=False` が常に書き込みをブロックします。`committed auth_mode=disabled` はリポジトリに安全に保たれています。

---

## OAuth 方式（代替）

サービスアカウントの代わりにOAuthを使用する場合:

1. **APIs & Services → Credentials → OAuth 2.0 Client IDs** を作成
2. アプリケーションタイプ: **Desktop app**
3. ダウンロードしたJSONを `credentials/oauth-client.json` に配置
4. `config/workspace_settings.json` の `connector.auth_mode` を `"oauth"` に変更
5. 初回実行時にブラウザが開き、Googleアカウントでの承認が求められます（`token.json` が生成されます）

---

## セキュリティ チェックリスト

実際の接続を有効にする前に確認してください:

- [ ] `credentials/` フォルダが `.gitignore` に含まれている
- [ ] `git status` で credential ファイルが表示されないことを確認
- [ ] `git log --all --full-history -- "credentials/*.json"` で過去のコミットに含まれていないことを確認
- [ ] サービスアカウントの権限は必要最小限（Viewer / Editor のみ）
- [ ] スプレッドシートはサービスアカウントとのみ共有（パブリック共有しない）
- [ ] `config/workspace_settings.json` に実際の認証情報が含まれていないことを確認

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `gspread not installed` | パッケージ未インストール | `pip install gspread google-auth` |
| `認証ファイルなし` | ファイルパスが間違っている | `connector.service_account_file` のパスを確認 |
| `403 Forbidden` | スプレッドシートが共有されていない | Step 3 を再確認 |
| `spreadsheet_id 未設定` | IDがコピーされていない | Google SheetsのURLから再コピー |
| `token.json` がgitに表示される | `.gitignore` が効いていない | `.gitignore` に `token.json` が含まれているか確認 |

---

## auth_mode の切り替え方法

`config/workspace_settings.json` の `connector.auth_mode` を変更するだけです:

| 値 | 動作 |
|----|------|
| `"disabled"` | ドライランのみ。API呼び出しなし（**デフォルト・推奨**） |
| `"service_account"` | サービスアカウントJSONで認証 |
| `"oauth"` | OAuthフローで認証 |

**いつでも `"disabled"` に戻すことができます。** 設定を元に戻すだけでAPI呼び出しは完全に停止します。
