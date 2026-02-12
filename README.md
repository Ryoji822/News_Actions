# News_Actions

AI・生成AI関連ニュースを毎日自動収集し、月別ディレクトリにMarkdownで保存するGitHub Actionsワークフロー。

## 仕組み

- **実行スケジュール**: 毎日 09:30 JST (00:30 UTC)
- **ニュース収集**: OpenCode (z.ai) がWeb検索でAI関連ニュースを収集・要約
- **保存形式**: `news/YYYY-MM/YYYY-MM-DD.md`
- **自動コミット**: 収集結果をgithub-actions botが自動コミット・プッシュ

## ディレクトリ構成

```
News_Actions/
├── .github/
│   └── workflows/
│       └── daily-news.yml    # GitHub Actionsワークフロー
├── opencode.json              # OpenCode z.ai プロバイダー設定
├── news/
│   ├── 2026-02/
│   │   ├── 2026-02-11.md
│   │   ├── 2026-02-12.md
│   │   └── ...
│   ├── 2026-03/
│   │   └── ...
│   └── .gitkeep
└── README.md
```

## セットアップ

### 1. z.ai API キーの取得

1. [z.ai](https://z.ai) にログイン
2. [APIキー管理画面](https://z.ai/manage-apikey/apikey-list) でAPIキーを生成

### 2. GitHub Secretsの設定

1. リポジトリの **Settings** > **Secrets and variables** > **Actions** を開く
2. **New repository secret** をクリック
3. 以下を設定:
   - **Name**: `Z_AI_API_KEY`
   - **Secret**: z.aiで取得したAPIキー

### 3. OpenCode GitHub Appのインストール

1. [OpenCode Agent GitHub App](https://github.com/apps/opencode-agent) にアクセス
2. このリポジトリにインストール・認可

### 4. ワークフローの有効化

- リポジトリの **Actions** タブで、ワークフローが有効になっていることを確認
- 手動テスト: **Actions** > **Daily AI News** > **Run workflow** で即時実行可能

## 手動実行

GitHub Actionsの `workflow_dispatch` トリガーにより、手動でも実行できます:

1. リポジトリの **Actions** タブを開く
2. **Daily AI News** ワークフローを選択
3. **Run workflow** をクリック

## 注意事項

- スケジュール実行はGitHub側の負荷により数分〜数十分遅延する場合があります
- パブリックリポジトリでは、60日間アクティビティがないとスケジュール実行が自動停止します（プライベートリポジトリでは適用されません）
- z.aiのサブスクリプションプランにより、1日のリクエスト上限が異なります
