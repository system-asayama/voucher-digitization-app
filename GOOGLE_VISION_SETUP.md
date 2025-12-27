# Google Cloud Vision API セットアップガイド

## 概要

このアプリケーションは、Google Cloud Vision APIを使用してOCR（光学文字認識）の精度を大幅に向上させています。

**精度向上**
- Tesseract OCR: 60-70%
- Google Cloud Vision API: **85-95%**

## 料金

- **月1,000枚まで無料**
- 1,000枚以降: $1.50 / 1,000枚

詳細: https://cloud.google.com/vision/pricing

## セットアップ手順

### 1. Google Cloud Platformプロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成
3. プロジェクト名を入力（例: `trademark-digitization-app`）

### 2. Vision APIの有効化

1. Google Cloud Consoleで「APIとサービス」→「ライブラリ」を開く
2. 「Cloud Vision API」を検索
3. 「有効にする」をクリック

### 3. サービスアカウントの作成

1. 「IAMと管理」→「サービスアカウント」を開く
2. 「サービスアカウントを作成」をクリック
3. サービスアカウント名を入力（例: `vision-api-service`）
4. ロールを選択: **「Cloud Vision API ユーザー」**
5. 「完了」をクリック

### 4. 認証キー（JSONファイル）の作成

1. 作成したサービスアカウントをクリック
2. 「キー」タブを開く
3. 「鍵を追加」→「新しい鍵を作成」
4. キーのタイプ: **JSON**
5. 「作成」をクリック
6. JSONファイルがダウンロードされる

### 5. Herokuへの環境変数設定

#### 方法1: Heroku CLI

```bash
# JSONファイルの内容をbase64エンコード
cat path/to/your-service-account-key.json | base64 > encoded-key.txt

# Herokuに環境変数を設定
heroku config:set GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat encoded-key.txt)" --app your-app-name
```

#### 方法2: Heroku Dashboard

1. Herokuダッシュボードでアプリを選択
2. 「Settings」タブを開く
3. 「Config Vars」セクションで「Reveal Config Vars」をクリック
4. 以下の環境変数を追加:
   - **KEY**: `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - **VALUE**: JSONファイルの内容をbase64エンコードした文字列

### 6. アプリケーションの再起動

```bash
heroku restart --app your-app-name
```

## ローカル開発環境でのセットアップ

### 環境変数の設定

```bash
# .envファイルを作成
echo "GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account-key.json" > .env
```

### 実行

```bash
# 依存関係をインストール
pip install -r requirements.txt

# アプリケーションを起動
python run.py
```

## トラブルシューティング

### エラー: "GOOGLE_APPLICATION_CREDENTIALS環境変数が設定されていません"

**原因**: 環境変数が正しく設定されていない

**解決策**:
1. Herokuの環境変数を確認
2. JSONファイルが正しくbase64エンコードされているか確認
3. アプリケーションを再起動

### エラー: "Google Vision API Error: ..."

**原因**: APIが有効化されていない、または認証情報が無効

**解決策**:
1. Google Cloud ConsoleでVision APIが有効になっているか確認
2. サービスアカウントのロールが正しいか確認
3. JSONファイルが最新のものか確認

### フォールバック機能

Google Cloud Vision APIが利用できない場合、自動的にTesseract OCRにフォールバックします。

## 使用状況の確認

Google Cloud Consoleの「APIとサービス」→「ダッシュボード」で使用状況を確認できます。

## セキュリティ

- JSONファイルは**絶対にGitにコミットしない**
- `.gitignore`に追加済み
- 環境変数として管理
