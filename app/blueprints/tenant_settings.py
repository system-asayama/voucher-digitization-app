# -*- coding: utf-8 -*-
"""
テナント設定Blueprint
AI設定を含む
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..utils.db import get_db, _sql
from ..utils.ai_helper import get_ai_model_info

bp = Blueprint('tenant_settings', __name__, url_prefix='/tenant/settings')


@bp.route('/')
def index():
    """テナント設定画面"""
    # セッションからテナントIDを取得
    tenant_id = session.get('tenant_id')
    
    if not tenant_id:
        flash('テナント情報が見つかりません', 'error')
        return redirect(url_for('auth.login'))
    
    conn = get_db()
    cur = conn.cursor()
    
    # テナント情報を取得
    cur.execute(_sql(conn, 'SELECT * FROM "T_テナント" WHERE id = %s'), (tenant_id,))
    tenant = cur.fetchone()
    
    if not tenant:
        flash('テナント情報が見つかりません', 'error')
        return redirect(url_for('auth.login'))
    
    # AI設定を取得
    ai_model = tenant[4] if len(tenant) > 4 else 'gemini-1.5-flash'  # ai_model
    openai_api_key = tenant[5] if len(tenant) > 5 else None  # openai_api_key
    google_api_key = tenant[6] if len(tenant) > 6 else None  # google_api_key
    anthropic_api_key = tenant[7] if len(tenant) > 7 else None  # anthropic_api_key
    
    # AIモデル情報を取得
    models = [
        {
            'value': 'gemini-1.5-flash',
            'info': get_ai_model_info('gemini-1.5-flash'),
            'selected': ai_model == 'gemini-1.5-flash',
        },
        {
            'value': 'gpt-4o-mini',
            'info': get_ai_model_info('gpt-4o-mini'),
            'selected': ai_model == 'gpt-4o-mini',
        },
        {
            'value': 'gpt-4o',
            'info': get_ai_model_info('gpt-4o'),
            'selected': ai_model == 'gpt-4o',
        },
    ]
    
    return render_template(
        'tenant_settings.html',
        tenant=tenant,
        ai_model=ai_model,
        models=models,
        openai_api_key=openai_api_key,
        google_api_key=google_api_key,
        anthropic_api_key=anthropic_api_key,
    )


@bp.route('/update', methods=['POST'])
def update():
    """テナント設定を更新"""
    tenant_id = session.get('tenant_id')
    
    if not tenant_id:
        flash('テナント情報が見つかりません', 'error')
        return redirect(url_for('auth.login'))
    
    # フォームデータを取得
    ai_model = request.form.get('ai_model', 'gemini-1.5-flash')
    openai_api_key = request.form.get('openai_api_key', '').strip() or None
    google_api_key = request.form.get('google_api_key', '').strip() or None
    anthropic_api_key = request.form.get('anthropic_api_key', '').strip() or None
    
    conn = get_db()
    cur = conn.cursor()
    
    # AI設定を更新
    cur.execute(_sql(conn, '''
        UPDATE "T_テナント"
        SET ai_model = %s,
            openai_api_key = %s,
            google_api_key = %s,
            anthropic_api_key = %s
        WHERE id = %s
    '''), (ai_model, openai_api_key, google_api_key, anthropic_api_key, tenant_id))
    
    flash('AI設定を更新しました', 'success')
    return redirect(url_for('tenant_settings.index'))
