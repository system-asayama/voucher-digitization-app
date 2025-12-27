from __future__ import annotations
import os
from flask import Flask

def create_app() -> Flask:
    """
    Flaskアプリケーションを生成して返します。
    Herokuで実行する場合もローカルで実行する場合もこの関数が呼ばれます。
    """
    # Google Cloud認証情報のセットアップ
    from .utils.google_vision_helper import setup_google_credentials
    setup_google_credentials()
    
    app = Flask(__name__)

    # SECRET_KEY設定
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # デフォルト設定を読み込み（環境変数が無ければ標準値を使う）
    app.config.update(
        APP_NAME=os.getenv("APP_NAME", "login-system-app"),
        ENVIRONMENT=os.getenv("ENV", "dev"),
        DEBUG=os.getenv("DEBUG", "1") in ("1", "true", "True"),
        VERSION=os.getenv("APP_VERSION", "0.1.0"),
        TZ=os.getenv("TZ", "Asia/Tokyo"),
    )

    # config.py があれば上書き
    try:
        from .config import settings  # type: ignore
        app.config.update(
            ENVIRONMENT=getattr(settings, "ENV", app.config["ENVIRONMENT"]),
            DEBUG=getattr(settings, "DEBUG", app.config["DEBUG"]),
            VERSION=getattr(settings, "VERSION", app.config["VERSION"]),
            TZ=getattr(settings, "TZ", app.config["TZ"]),
        )
    except Exception:
        # 存在しない場合は無視
        pass

    # logging.py があればロガーを初期化
    try:
        from .logging import setup_logging  # type: ignore
        setup_logging(debug=app.config["DEBUG"])
    except Exception:
        pass

    # CSRF トークンをテンプレートで使えるようにする
    @app.context_processor
    def inject_csrf():
        from .utils import get_csrf
        return {"get_csrf": get_csrf}

    # テナント/店舗情報をテンプレートで使えるようにする
    @app.context_processor
    def inject_context_info():
        from flask import session, url_for
        from .utils import get_db, _sql
        
        context = {
            'current_tenant_name': None,
            'current_store_name': None,
        }
        
        # ロールに応じたマイページURLを設定
        role = session.get('role')
        if role == 'system_admin':
            context['mypage_url'] = url_for('system_admin.mypage')
        elif role == 'tenant_admin':
            context['mypage_url'] = url_for('tenant_admin.mypage')
        elif role == 'admin':
            context['mypage_url'] = url_for('admin.mypage')
        elif role == 'employee':
            context['mypage_url'] = url_for('employee.mypage')
        else:
            context['mypage_url'] = url_for('auth.index')
        
        # テナント情報を取得
        tenant_id = session.get('tenant_id')
        if tenant_id:
            try:
                conn = get_db()
                cur = conn.cursor()
                sql = _sql(conn, 'SELECT "名称" FROM "T_テナント" WHERE id=%s')
                cur.execute(sql, (tenant_id,))
                row = cur.fetchone()
                if row:
                    context['current_tenant_name'] = row[0]
                conn.close()
            except Exception:
                pass
        
        # 店舗情報を取得
        store_id = session.get('store_id')
        if store_id:
            try:
                conn = get_db()
                cur = conn.cursor()
                sql = _sql(conn, 'SELECT "名称", tenant_id FROM "T_店舗" WHERE id=%s')
                cur.execute(sql, (store_id,))
                row = cur.fetchone()
                if row:
                    context['current_store_name'] = row[0]
                    # 店舗のテナント情報も取得
                    if not context['current_tenant_name'] and row[1]:
                        cur2 = conn.cursor()
                        sql2 = _sql(conn, 'SELECT "名称" FROM "T_テナント" WHERE id=%s')
                        cur2.execute(sql2, (row[1],))
                        row2 = cur2.fetchone()
                        if row2:
                            context['current_tenant_name'] = row2[0]
                conn.close()
            except Exception:
                pass
        
        return context

    # データベース初期化
    try:
        from .utils import get_db
        conn = get_db()
        try:
            conn.close()
        except:
            pass
        print("✅ データベース初期化完了")
    except Exception as e:
        print(f"⚠️ データベース初期化エラー: {e}")

    # blueprints 登録
    try:
        from .blueprints.health import bp as health_bp  # type: ignore
        app.register_blueprint(health_bp)
    except Exception:
        pass

    # 認証関連blueprints
    try:
        from .blueprints.auth import bp as auth_bp
        app.register_blueprint(auth_bp)
    except Exception as e:
        print(f"⚠️ auth blueprint 登録エラー: {e}")

    try:
        from .blueprints.system_admin import bp as system_admin_bp
        app.register_blueprint(system_admin_bp)
    except Exception as e:
        print(f"⚠️ system_admin blueprint 登録エラー: {e}")

    try:
        from .blueprints.tenant_admin import bp as tenant_admin_bp
        app.register_blueprint(tenant_admin_bp)
    except Exception as e:
        print(f"⚠️ tenant_admin blueprint 登録エラー: {e}")

    try:
        from .blueprints.admin import bp as admin_bp
        app.register_blueprint(admin_bp)
    except Exception as e:
        print(f"⚠️ admin blueprint 登録エラー: {e}")

    try:
        from .blueprints.employee import bp as employee_bp
        app.register_blueprint(employee_bp)
    except Exception as e:
        print(f"⚠️ employee blueprint 登録エラー: {e}")

    try:
        from .blueprints.voucher import bp as voucher_bp
        app.register_blueprint(voucher_bp)
    except Exception as e:
        print(f"⚠️ voucher blueprint 登録エラー: {e}")

    try:
        from .blueprints.company import bp as company_bp
        app.register_blueprint(company_bp)
    except Exception as e:
        print(f"⚠️ company blueprint 登録エラー: {e}")

    try:
        from .blueprints.tenant_settings import bp as tenant_settings_bp
        app.register_blueprint(tenant_settings_bp)
    except Exception as e:
        print(f"⚠️ tenant_settings blueprint 登録エラー: {e}")

    try:
        from .blueprints.journal import bp as journal_bp
        app.register_blueprint(journal_bp)
    except Exception as e:
        print(f"⚠️ journal blueprint 登録エラー: {e}")

    try:
        from .blueprints.export import bp as export_bp
        app.register_blueprint(export_bp)
    except Exception as e:
        print(f"⚠️ export blueprint 登録エラー: {e}")

    # エラーハンドラ
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        return render_template('500.html'), 500

    return app
