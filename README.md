# Voucher Digitization App

証憑データ化システム - レシート・領収書のOCR読み取り、国税庁API連携、自動仕訳生成

## 概要

会計事務所向けの証憑データ化システムです。レシート・領収書から企業情報を自動抽出し、国税庁APIで企業情報を検索して仕訳を自動生成します。

## 主要機能

### 1. 認証・権限管理システム
- **システム管理者 (system_admin)**: 全テナント横断の最高権限
- **テナント管理者 (tenant_admin)**: テナント単位の管理者
- **管理者 (admin)**: 店舗/拠点などの管理者
- **従業員 (employee)**: 一般従業員

### 2. 証憑データ化機能（実装予定）
- レシート・領収書のOCR読み取り
- 電話番号・住所の自動抽出
- 国税庁インボイス登録番号検索API連携
- 企業情報の自動取得（会社名、事業概要、インボイス登録有無）

### 3. 仕訳自動生成機能（実装予定）
- 取引内容の自動分類
- 勘定科目の自動推定
- 仕訳データの自動生成

### 4. 会計ソフト連携（実装予定）
- CSV出力機能
- 弥生会計、freee等との連携

## 技術スタック

### バックエンド
- **フレームワーク**: Flask 3.0.0
- **データベース**: PostgreSQL（psycopg2-binary 2.9.9）
- **ORM**: SQLAlchemy 2.0.36
- **Webサーバー**: Gunicorn 23.0.0（本番環境）

### セキュリティ
- パスワードハッシュ化（werkzeug.security）
- CSRF保護
- セッション管理
- ロールベースアクセス制御

## データベーススキーマ

### T_管理者
システム管理者、テナント管理者、管理者のログイン情報を管理

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| login_id | TEXT | ログインID（ユニーク） |
| name | TEXT | 氏名 |
| password_hash | TEXT | パスワードハッシュ |
| role | TEXT | ロール（system_admin/tenant_admin/admin） |
| tenant_id | INTEGER | テナントID |
| active | INTEGER | 有効フラグ |
| is_owner | INTEGER | オーナーフラグ |
| can_manage_admins | INTEGER | 管理者管理権限フラグ |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

### T_従業員
従業員のログイン情報を管理

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| email | TEXT | メールアドレス（ユニーク） |
| login_id | TEXT | ログインID（ユニーク） |
| name | TEXT | 氏名 |
| password_hash | TEXT | パスワードハッシュ |
| tenant_id | INTEGER | テナントID |
| role | TEXT | ロール（employee） |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

### T_テナント
テナント情報を管理

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| 名称 | TEXT | テナント名 |
| slug | TEXT | スラッグ（ユニーク） |
| 有効 | INTEGER | 有効フラグ |
| created_at | TIMESTAMP | 作成日時 |

### T_店舗
店舗情報を管理

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| tenant_id | INTEGER | テナントID |
| 名称 | TEXT | 店舗名 |
| slug | TEXT | スラッグ |
| 有効 | INTEGER | 有効フラグ |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

### T_テナント管理者_テナント
テナント管理者とテナントの多対多関係

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| tenant_admin_id | INTEGER | テナント管理者ID |
| tenant_id | INTEGER | テナントID |
| created_at | TIMESTAMP | 作成日時 |

### T_管理者_店舗
管理者と店舗の多対多関係

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| admin_id | INTEGER | 管理者ID |
| store_id | INTEGER | 店舗ID |
| created_at | TIMESTAMP | 作成日時 |

### T_従業員_店舗
従業員と店舗の多対多関係

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| employee_id | INTEGER | 従業員ID |
| store_id | INTEGER | 店舗ID |
| created_at | TIMESTAMP | 作成日時 |

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example`を`.env`にコピーして編集:

```bash
cp .env.example .env
```

`.env`ファイルの内容:

```env
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=postgresql://postgres:password@localhost:5432/voucher_dev
```

### 3. アプリケーションの起動

#### ローカル開発環境

```bash
python wsgi.py
```

または

```bash
flask run
```

#### 本番環境（Heroku等）

```bash
gunicorn wsgi:app
```

## ルーティング

### 認証関連
- `/` - トップページ（ロール別リダイレクト）
- `/select_login` - ログイン選択画面
- `/first_admin_setup` - 初回管理者セットアップ
- `/system_admin_login` - システム管理者ログイン
- `/tenant_admin_login` - テナント管理者ログイン
- `/admin_login` - 管理者ログイン
- `/employee_login` - 従業員ログイン
- `/logout` - ログアウト

### ダッシュボード
- `/system_admin/` - システム管理者ダッシュボード
- `/tenant_admin/` - テナント管理者ダッシュボード
- `/admin/` - 管理者ダッシュボード
- `/employee/mypage` - 従業員マイページ

## ディレクトリ構造

```
voucher-digitization-app/
├── app/
│   ├── __init__.py          # アプリケーションファクトリ
│   ├── config.py            # 設定ファイル
│   ├── logging.py           # ロギング設定
│   ├── utils/               # ユーティリティモジュール
│   │   ├── __init__.py
│   │   ├── db.py            # DB接続・スキーマ初期化
│   │   ├── security.py      # セキュリティ関連
│   │   └── decorators.py    # デコレータ（require_roles等）
│   ├── blueprints/          # Blueprint（機能別ルート）
│   │   ├── __init__.py
│   │   ├── health.py        # ヘルスチェック
│   │   ├── auth.py          # 認証関連
│   │   ├── system_admin.py  # システム管理者
│   │   ├── tenant_admin.py  # テナント管理者
│   │   ├── admin.py         # 管理者
│   │   └── employee.py      # 従業員
│   └── templates/           # Jinjaテンプレート
├── database/                # SQLiteデータベース（.gitignore）
├── requirements.txt         # 依存パッケージ
├── .env.example             # 環境変数サンプル
├── wsgi.py                  # WSGIエントリーポイント
├── Procfile                 # Heroku設定
└── README.md                # このファイル
```

## 開発ロードマップ

### Phase 1: 認証・権限管理システム（完了）
- [x] 4ロール認証システム
- [x] マルチテナント・マルチ店舗対応
- [x] ロールベースアクセス制御

### Phase 2: OCR機能（実装予定）
- [ ] レシート・領収書の画像アップロード
- [ ] OCRによる文字認識
- [ ] 電話番号・住所の抽出

### Phase 3: 国税庁API連携（実装予定）
- [ ] 国税庁インボイス登録番号検索API連携
- [ ] 企業情報の自動取得
- [ ] データベースへの保存

### Phase 4: 仕訳自動生成（実装予定）
- [ ] 取引内容の自動分類
- [ ] 勘定科目の自動推定
- [ ] 仕訳データの生成

### Phase 5: 会計ソフト連携（実装予定）
- [ ] CSV出力機能
- [ ] 弥生会計連携
- [ ] freee連携

## ライセンス

MIT License
