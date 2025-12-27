# デプロイメントガイド

証憑データ化システムのデプロイ手順

## Herokuへのデプロイ

### 前提条件

- Heroku CLIがインストールされていること
- Herokuアカウントを持っていること
- Gitがインストールされていること

### 1. Heroku CLIのインストール

**macOS:**
```bash
brew tap heroku/brew && brew install heroku
```

**Ubuntu/Debian:**
```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

**Windows:**
[Heroku CLI公式サイト](https://devcenter.heroku.com/articles/heroku-cli)からインストーラーをダウンロード

### 2. Herokuにログイン

```bash
heroku login
```

### 3. Herokuアプリの作成

```bash
cd voucher-digitization-app
heroku create your-app-name
```

アプリ名を指定しない場合、ランダムな名前が生成されます：
```bash
heroku create
```

### 4. PostgreSQLアドオンの追加

```bash
heroku addons:create heroku-postgresql:mini
```

データベースURLは自動的に`DATABASE_URL`環境変数に設定されます。

### 5. Tesseract Buildpackの追加

```bash
heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt
heroku buildpacks:add --index 2 heroku/python
```

Buildpackの順序を確認：
```bash
heroku buildpacks
```

出力例：
```
=== your-app-name Buildpack URLs
1. https://github.com/heroku/heroku-buildpack-apt
2. heroku/python
```

### 6. 環境変数の設定

```bash
# SECRET_KEYの生成と設定
heroku config:set SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

# その他の環境変数（必要に応じて）
heroku config:set UPLOAD_FOLDER=uploads
heroku config:set MAX_CONTENT_LENGTH=16777216
```

環境変数の確認：
```bash
heroku config
```

### 7. デプロイ

```bash
git push heroku master
```

または、別のブランチからデプロイする場合：
```bash
git push heroku your-branch:master
```

### 8. アプリケーションを開く

```bash
heroku open
```

### 9. ログの確認

```bash
heroku logs --tail
```

### 10. データベースの確認

```bash
heroku pg:info
```

データベースに直接接続：
```bash
heroku pg:psql
```

## トラブルシューティング

### デプロイエラー

**エラー: `Tesseract not found`**

解決策：
1. `Aptfile`が存在することを確認
2. Buildpackの順序を確認（apt buildpackが最初）
3. 再デプロイ

```bash
git commit --allow-empty -m "Rebuild with apt buildpack"
git push heroku master
```

**エラー: `Database connection failed`**

解決策：
1. PostgreSQLアドオンが追加されているか確認
   ```bash
   heroku addons
   ```
2. `DATABASE_URL`環境変数が設定されているか確認
   ```bash
   heroku config:get DATABASE_URL
   ```

**エラー: `Application error`**

解決策：
1. ログを確認
   ```bash
   heroku logs --tail
   ```
2. 環境変数を確認
   ```bash
   heroku config
   ```

### パフォーマンス最適化

**Dynoのスケールアップ**

```bash
# Hobby dynoにアップグレード
heroku ps:scale web=1:hobby

# Standard dynoにアップグレード
heroku ps:scale web=1:standard-1x
```

**PostgreSQLのアップグレード**

```bash
# Standard-0プランにアップグレード
heroku addons:upgrade heroku-postgresql:standard-0
```

### メンテナンスモード

**メンテナンスモードの有効化**

```bash
heroku maintenance:on
```

**メンテナンスモードの無効化**

```bash
heroku maintenance:off
```

## 本番環境の設定

### 1. カスタムドメインの設定

```bash
heroku domains:add www.yourdomain.com
```

DNS設定：
```
CNAME www.yourdomain.com -> your-app-name.herokuapp.com
```

### 2. SSL証明書の設定

Herokuは自動的にSSL証明書を提供します（Automated Certificate Management）。

カスタムドメインを追加すると、自動的にSSL証明書が発行されます。

### 3. バックアップの設定

```bash
# 手動バックアップ
heroku pg:backups:capture

# バックアップのスケジュール設定（Standard以上のプランで利用可能）
heroku pg:backups:schedule DATABASE_URL --at '02:00 Asia/Tokyo'
```

バックアップの確認：
```bash
heroku pg:backups
```

### 4. モニタリング

**New Relicアドオンの追加**

```bash
heroku addons:create newrelic:wayne
```

**Papertrailアドオンの追加（ログ管理）**

```bash
heroku addons:create papertrail:choklad
```

## その他のデプロイオプション

### Railway

1. [Railway](https://railway.app/)にアクセス
2. GitHubリポジトリを接続
3. PostgreSQLサービスを追加
4. 環境変数を設定
5. 自動デプロイ

### Render

1. [Render](https://render.com/)にアクセス
2. 「New Web Service」を作成
3. GitHubリポジトリを接続
4. PostgreSQLデータベースを作成
5. 環境変数を設定
6. デプロイ

### AWS (Elastic Beanstalk)

1. Elastic Beanstalk CLIをインストール
2. アプリケーションを初期化
   ```bash
   eb init
   ```
3. 環境を作成
   ```bash
   eb create production
   ```
4. デプロイ
   ```bash
   eb deploy
   ```

## セキュリティチェックリスト

- [ ] `SECRET_KEY`を本番環境用に変更
- [ ] デフォルトの管理者パスワードを変更
- [ ] HTTPS接続を強制
- [ ] データベースのバックアップを設定
- [ ] ログ監視を設定
- [ ] エラー通知を設定
- [ ] レート制限を実装（必要に応じて）
- [ ] ファイルアップロードのサイズ制限を確認

## パフォーマンスチェックリスト

- [ ] 静的ファイルのキャッシュを有効化
- [ ] データベースインデックスを最適化
- [ ] 画像の最適化（アップロード時）
- [ ] OCR処理の非同期化（必要に応じて）
- [ ] ログレベルを適切に設定

## 運用チェックリスト

- [ ] 定期的なバックアップの確認
- [ ] ログの定期的な確認
- [ ] パフォーマンスメトリクスの監視
- [ ] セキュリティアップデートの適用
- [ ] ユーザーフィードバックの収集
