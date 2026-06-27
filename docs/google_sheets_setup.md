# Google Sheets セットアップガイド — Creator Factory OS v5.2 Phase 3

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

## 前提パッケージ（オプション）

Google Sheets連携には以下のパッケージが必要です。インストールしない場合はドライランモードで動作します。

```bash
pip install gspread google-auth
```

インストール後、Development Studio → Workspace Sync タブで依存パッケージのステータスが更新されます。

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
4. ロールは **Editor** または **Viewer** を付与
5. 作成後、サービスアカウントをクリック → **Keys タブ** → **Add Key → JSON**
6. ダウンロードされたJSONファイルをプロジェクトの `credentials/` フォルダに配置:
   ```
   credentials/service-account.json
   ```
   ※ このファイルは `.gitignore` により自動的に除外されます

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

## Step 4: config/workspace_settings.json の更新

`config/workspace_settings.json` の `connector` セクションと `google_sheets` セクションを更新します:

```json
{
  "connector": {
    "auth_mode": "service_account",
    "service_account_file": "credentials/service-account.json",
    "oauth_client_file": ""
  },
  "google_sheets": {
    "spreadsheet_id": "YOUR_SPREADSHEET_ID_HERE",
    "worksheet_name": "KPI",
    "range": "A1"
  }
}
```

**注意:**
- `auth_mode` を `"service_account"` に変更
- `service_account_file` にローカルパスを設定（ファイル内容は記載しない）
- `spreadsheet_id` に実際のIDを設定

---

## Step 5: gspread readiness チェック

Development Studio → Tab 10 (Workspace Sync) → **Phase 3 Readiness Checklist** で以下を確認:

| チェック項目 | 期待値 |
|-------------|--------|
| gspread インストール | ✅ |
| google-auth インストール | ✅ |
| auth_mode | service_account |
| 認証ファイルパス設定 | ✅ |
| 認証ファイル存在確認 | ✅ |
| spreadsheet_id 設定 | ✅ |

すべて ✅ になると **Manual Execute** ボタンが有効化されます（Phase 3+ 実装後）。

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
