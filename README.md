# 証憑データ化システム (Voucher Digitization App)

会計事務所向けのレシート・領収書自動読み取り・仕訳生成システム

## 概要

証憑（レシート、領収書、カードの利用履歴）から電話番号や住所を読み取り、国税庁のインボイス登録APIを使用して企業情報を自動検索し、仕訳を自動生成する会計事務所向けアプリケーションです。

## 主要機能

### 1. 認証・ユーザー管理 ✅
- 4ロール認証システム（システム管理者、テナント管理者、管理者、従業員）
- マルチテナント・マルチ店舗対応
- ロールベースアクセス制御（RBAC）
- CSRF保護とセッション管理

### 2. 証憑管理 ✅
- レシート・領収書の画像アップロード
- OCR自動読み取り（Tesseract）
- 電話番号、住所、郵便番号、金額、日付の自動抽出
- 証憑一覧・詳細表示・編集・削除

### 3. 企業情報管理 ✅
- 国税庁インボイス登録API連携
- インボイス登録番号、法人番号、会社名による検索
- 企業情報の自動取得と登録
- 企業情報一覧・詳細表示・編集・削除

### 4. 仕訳自動生成 ✅
- 証憑データから仕訳を自動生成
- キーワードベースの勘定科目推定（50種類以上）
- 複数証憑の一括処理
- 仕訳の確認ワークフロー
- 仕訳一覧・詳細表示・編集・削除

### 5. CSV出力・会計ソフト連携 ✅
- 汎用CSV形式
- 弥生会計形式
- freee会計形式
- マネーフォワードクラウド会計形式
- PCA会計形式
- 日付範囲指定、確認済みフィルタ
- プレビュー機能

## 技術スタック

- **バックエンド**: Python 3.11, Flask 3.0.0
- **データベース**: PostgreSQL (本番), SQLite (開発)
- **ORM**: SQLAlchemy 2.0.36
- **OCR**: Tesseract, OpenCV, Pillow, pytesseract
- **Webサーバー**: Gunicorn (本番)
- **外部API**: 国税庁インボイス登録API

## システム要件

- Python 3.11以上
- PostgreSQL 12以上（本番環境）
- Tesseract OCR 4.0以上
- 推奨メモリ: 2GB以上

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/system-asayama/voucher-digitization-app.git
cd voucher-digitization-app
```

### 2. 仮想環境の作成と有効化

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. Tesseract OCRのインストール

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-jpn
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
- [Tesseract公式サイト](https://github.com/UB-Mannheim/tesseract/wiki)からインストーラーをダウンロード

### 5. 環境変数の設定

`.env`ファイルを作成し、以下の内容を設定：

```bash
# Flask設定
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=postgresql://username:password@localhost:5432/voucher_db

# または開発環境ではSQLite
# DATABASE_URL=sqlite:///database/voucher.db

# アップロード設定
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB
```

### 6. データベースの初期化

アプリケーションを起動すると、自動的にデータベースが初期化されます。

### 7. アプリケーションの起動

**開発環境:**
```bash
python wsgi.py
```

**本番環境:**
```bash
gunicorn wsgi:app
```

アプリケーションは `http://localhost:5000` でアクセス可能です。

## 初回セットアップ

1. ブラウザで `http://localhost:5000` にアクセス
2. 「初回管理者セットアップ」画面が表示されます
3. システム管理者のログインID、氏名、パスワードを設定
4. セットアップ完了後、設定したログインIDとパスワードでログイン

## ディレクトリ構造

```
voucher-digitization-app/
├── app/
│   ├── __init__.py           # Flaskアプリケーション初期化
│   ├── blueprints/           # Blueprint（機能モジュール）
│   │   ├── auth.py           # 認証
│   │   ├── system_admin.py   # システム管理者
│   │   ├── tenant_admin.py   # テナント管理者
│   │   ├── admin.py          # 管理者管理
│   │   ├── employee.py       # 従業員管理
│   │   ├── tenant.py         # テナント管理
│   │   ├── store.py          # 店舗管理
│   │   ├── voucher.py        # 証憑管理
│   │   ├── company.py        # 企業情報管理
│   │   ├── journal.py        # 仕訳管理
│   │   └── export.py         # CSV出力
│   ├── templates/            # HTMLテンプレート
│   ├── static/               # 静的ファイル（CSS, JS, 画像）
│   └── utils/                # ユーティリティ
│       ├── db.py             # データベース接続・スキーマ
│       ├── decorators.py     # デコレータ
│       ├── ocr.py            # OCR処理
│       ├── nta_api.py        # 国税庁API連携
│       ├── journal_generator.py  # 仕訳自動生成
│       └── export.py         # CSV出力
├── uploads/                  # アップロードファイル
├── database/                 # SQLiteデータベース（開発環境）
├── requirements.txt          # Pythonパッケージ
├── wsgi.py                   # アプリケーションエントリーポイント
├── Procfile                  # Heroku設定
└── README.md                 # このファイル
```

## 使い方

### 1. ログイン
- システム管理者またはテナント管理者でログイン

### 2. 証憑のアップロード
1. 「証憑管理」→「証憑アップロード」
2. レシート・領収書の画像をアップロード
3. OCRが自動実行され、情報が抽出される

### 3. 企業情報の検索・登録
1. 「企業情報」→「企業検索」
2. 電話番号やインボイス登録番号で検索
3. 国税庁APIから企業情報を取得
4. 「この企業を登録」で登録

### 4. 仕訳の自動生成
1. 「仕訳管理」→「仕訳自動生成」
2. 証憑を選択
3. 「仕訳を生成」で自動生成
4. 生成された仕訳を確認・編集

### 5. CSV出力
1. 「CSV出力」
2. 出力形式を選択（弥生会計、freeeなど）
3. 期間を指定
4. 「ダウンロード」でCSV取得
5. 会計ソフトにインポート

## Herokuへのデプロイ

### 1. Herokuアプリの作成

```bash
heroku create your-app-name
```

### 2. PostgreSQLアドオンの追加

```bash
heroku addons:create heroku-postgresql:mini
```

### 3. 環境変数の設定

```bash
heroku config:set SECRET_KEY=your-secret-key-here
```

### 4. Tesseract Buildpackの追加

```bash
heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt
```

`Aptfile`を作成：
```
tesseract-ocr
tesseract-ocr-jpn
```

### 5. デプロイ

```bash
git push heroku master
```

### 6. アプリケーションを開く

```bash
heroku open
```

## データベーススキーマ

### 既存テーブル（ログインシステム）
- T_管理者（システム管理者、テナント管理者、管理者）
- T_従業員（従業員）
- T_テナント（テナント情報）
- T_店舗（店舗情報）
- T_テナント管理者_テナント（多対多関係）
- T_管理者_店舗（多対多関係）
- T_従業員_店舗（多対多関係）

### 新規テーブル（証憑データ化システム）
- **T_証憑**: レシート・領収書データ
- **T_企業情報**: 国税庁APIから取得した企業データ
- **T_仕訳**: 自動生成された仕訳データ

## トラブルシューティング

### OCRが動作しない
- Tesseractがインストールされているか確認: `tesseract --version`
- 日本語言語パックがインストールされているか確認
- Windowsの場合、Tesseractのパスが環境変数に設定されているか確認

### データベース接続エラー
- `DATABASE_URL`が正しく設定されているか確認
- PostgreSQLサービスが起動しているか確認
- 開発環境ではSQLiteを使用することを推奨

### アップロードエラー
- `uploads/`ディレクトリが存在し、書き込み権限があるか確認
- `MAX_CONTENT_LENGTH`の設定を確認（デフォルト16MB）

### 国税庁API接続エラー
- インターネット接続を確認
- 国税庁APIのサービス状況を確認

## 開発ロードマップ

- [x] Phase 1: 認証・権限管理システム
- [x] Phase 2: OCR機能とレシート読み取り
- [x] Phase 3: 国税庁API連携と企業情報検索
- [x] Phase 4: 仕訳自動生成機能
- [x] Phase 5: CSV出力と会計ソフト連携
- [ ] Phase 6: モバイルアプリ対応（React Native）
- [ ] Phase 7: AI/機械学習による勘定科目推定の高度化

## ライセンス

このプロジェクトはプライベートリポジトリです。

## 開発者

system-asayama

## サポート

問題が発生した場合は、GitHubのIssuesで報告してください。
