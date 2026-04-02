# -*- coding: utf-8 -*-
"""
SQLAlchemy エンジン・セッション・Base の定義

app.db モジュールとして system_admin, tenant_admin, models_login, auto_migrations から
インポートされる SessionLocal, engine, Base を提供します。
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def _get_database_url() -> str:
    """
    DATABASE_URL 環境変数を取得し、HerokuのPostgres URLを
    SQLAlchemy 対応形式に変換して返す。
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # フォールバック: ローカル開発用 SQLite
        return "sqlite:///./dev.db"
    # Heroku の postgres:// を postgresql:// に変換（SQLAlchemy 2.x 対応）
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _get_database_url()

# PostgreSQL の場合は接続プールを設定、SQLite の場合はシンプルな設定
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
