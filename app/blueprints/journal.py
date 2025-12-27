# -*- coding: utf-8 -*-
"""
仕訳管理Blueprint
仕訳の自動生成、一覧表示、編集、確認
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime

from ..utils import get_db, _sql
from ..utils.decorators import require_roles
from ..utils.journal_generator import (
    generate_journal_entry,
    validate_journal_entry,
    get_account_subject_list,
    batch_generate_journal_entries
)

bp = Blueprint('journal', __name__, url_prefix='/journal')


@bp.route('/')
@require_roles(['system_admin', 'tenant_admin', 'admin', 'employee'])
def index():
    """仕訳一覧"""
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('テナントが選択されていません', 'error')
        return redirect(url_for('auth.index'))
    
    conn = get_db()
    cur = conn.cursor()
    
    # 仕訳一覧を取得
    sql = _sql(conn, '''
        SELECT 
            j.id,
            j.日付,
            j.借方勘定科目,
            j.借方金額,
            j.貸方勘定科目,
            j.貸方金額,
            j.摘要,
            j.自動生成フラグ,
            j.確認済みフラグ,
            j.created_at,
            c.会社名
        FROM "T_仕訳" j
        LEFT JOIN "T_企業情報" c ON j.企業情報ID = c.id
        WHERE j.tenant_id = %s
        ORDER BY j.日付 DESC, j.created_at DESC
    ''')
    cur.execute(sql, (tenant_id,))
    
    journals = cur.fetchall()
    conn.close()
    
    return render_template('journal_list.html', journals=journals)


@bp.route('/generate', methods=['GET', 'POST'])
@require_roles(['system_admin', 'tenant_admin', 'admin'])
def generate():
    """仕訳自動生成"""
    tenant_id = session.get('tenant_id')
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        # 未処理の証憑一覧を取得
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, '''
            SELECT 
                v.id,
                v.日付,
                v.金額,
                v.摘要,
                v.電話番号,
                v.住所,
                c.id as company_id,
                c.会社名
            FROM "T_証憑" v
            LEFT JOIN "T_企業情報" c ON v.電話番号 = c.電話番号
            WHERE v.tenant_id = %s AND v.ステータス = 'pending'
            ORDER BY v.created_at DESC
        ''')
        cur.execute(sql, (tenant_id,))
        
        vouchers = cur.fetchall()
        conn.close()
        
        return render_template('journal_generate.html', vouchers=vouchers)
    
    # POST: 仕訳生成実行
    try:
        voucher_ids = request.form.getlist('voucher_ids[]')
        
        if not voucher_ids:
            flash('証憑が選択されていません', 'error')
            return redirect(request.url)
        
        conn = get_db()
        cur = conn.cursor()
        
        generated_count = 0
        
        for voucher_id in voucher_ids:
            # 証憑データを取得
            sql = _sql(conn, '''
                SELECT 
                    v.*,
                    c.id as company_id,
                    c.会社名
                FROM "T_証憑" v
                LEFT JOIN "T_企業情報" c ON v.電話番号 = c.電話番号
                WHERE v.id = %s AND v.tenant_id = %s
            ''')
            cur.execute(sql, (voucher_id, tenant_id))
            voucher = cur.fetchone()
            
            if not voucher:
                continue
            
            # 証憑データを辞書に変換
            voucher_data = {
                'id': voucher[0] if isinstance(voucher, tuple) else voucher['id'],
                '金額': voucher[3] if isinstance(voucher, tuple) else voucher['金額'],
                '日付': voucher[4] if isinstance(voucher, tuple) else voucher['日付'],
                '摘要': voucher[5] if isinstance(voucher, tuple) else voucher['摘要'],
            }
            
            # 企業情報
            company_data = None
            if isinstance(voucher, tuple):
                if len(voucher) > 14 and voucher[14]:
                    company_data = {'会社名': voucher[15]}
            else:
                if voucher.get('company_id'):
                    company_data = {'会社名': voucher['会社名']}
            
            # 仕訳を生成
            journal_entry = generate_journal_entry(voucher_data, company_data)
            
            # バリデーション
            is_valid, errors = validate_journal_entry(journal_entry)
            if not is_valid:
                flash(f'証憑ID {voucher_id} の仕訳生成エラー: {", ".join(errors)}', 'warning')
                continue
            
            # データベースに保存
            sql = _sql(conn, '''
                INSERT INTO "T_仕訳" (
                    tenant_id,
                    証憑ID,
                    企業情報ID,
                    日付,
                    借方勘定科目,
                    借方金額,
                    借方補助科目,
                    貸方勘定科目,
                    貸方金額,
                    貸方補助科目,
                    摘要,
                    自動生成フラグ,
                    確認済みフラグ,
                    created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''')
            
            company_id = None
            if isinstance(voucher, tuple):
                company_id = voucher[14] if len(voucher) > 14 else None
            else:
                company_id = voucher.get('company_id')
            
            cur.execute(sql, (
                tenant_id,
                voucher_data['id'],
                company_id,
                journal_entry['日付'],
                journal_entry['借方勘定科目'],
                journal_entry['借方金額'],
                journal_entry['借方補助科目'],
                journal_entry['貸方勘定科目'],
                journal_entry['貸方金額'],
                journal_entry['貸方補助科目'],
                journal_entry['摘要'],
                journal_entry['自動生成フラグ'],
                journal_entry['確認済みフラグ'],
                user_id
            ))
            
            # 証憑のステータスを更新
            sql = _sql(conn, '''
                UPDATE "T_証憑"
                SET ステータス = 'processing'
                WHERE id = %s AND tenant_id = %s
            ''')
            cur.execute(sql, (voucher_id, tenant_id))
            
            generated_count += 1
        
        if hasattr(conn, 'commit'):
            conn.commit()
        
        conn.close()
        
        flash(f'{generated_count}件の仕訳を生成しました', 'success')
        return redirect(url_for('journal.index'))
        
    except Exception as e:
        flash(f'仕訳生成エラー: {str(e)}', 'error')
        return redirect(request.url)


@bp.route('/<int:journal_id>')
@require_roles(['system_admin', 'tenant_admin', 'admin', 'employee'])
def detail(journal_id):
    """仕訳詳細"""
    tenant_id = session.get('tenant_id')
    
    conn = get_db()
    cur = conn.cursor()
    
    sql = _sql(conn, '''
        SELECT 
            j.*,
            c.会社名,
            v.画像パス
        FROM "T_仕訳" j
        LEFT JOIN "T_企業情報" c ON j.企業情報ID = c.id
        LEFT JOIN "T_証憑" v ON j.証憑ID = v.id
        WHERE j.id = %s AND j.tenant_id = %s
    ''')
    cur.execute(sql, (journal_id, tenant_id))
    
    journal = cur.fetchone()
    conn.close()
    
    if not journal:
        flash('仕訳が見つかりません', 'error')
        return redirect(url_for('journal.index'))
    
    return render_template('journal_detail.html', journal=journal)


@bp.route('/<int:journal_id>/edit', methods=['GET', 'POST'])
@require_roles(['system_admin', 'tenant_admin', 'admin'])
def edit(journal_id):
    """仕訳編集"""
    tenant_id = session.get('tenant_id')
    
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == 'GET':
        sql = _sql(conn, '''
            SELECT * FROM "T_仕訳"
            WHERE id = %s AND tenant_id = %s
        ''')
        cur.execute(sql, (journal_id, tenant_id))
        journal = cur.fetchone()
        conn.close()
        
        if not journal:
            flash('仕訳が見つかりません', 'error')
            return redirect(url_for('journal.index'))
        
        # 勘定科目リストを取得
        account_subjects = get_account_subject_list()
        
        return render_template('journal_edit.html', journal=journal, account_subjects=account_subjects)
    
    # POST: 更新処理
    try:
        sql = _sql(conn, '''
            UPDATE "T_仕訳"
            SET 
                日付 = %s,
                借方勘定科目 = %s,
                借方金額 = %s,
                借方補助科目 = %s,
                貸方勘定科目 = %s,
                貸方金額 = %s,
                貸方補助科目 = %s,
                摘要 = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND tenant_id = %s
        ''')
        
        cur.execute(sql, (
            request.form.get('date'),
            request.form.get('debit_subject'),
            request.form.get('debit_amount'),
            request.form.get('debit_sub_subject'),
            request.form.get('credit_subject'),
            request.form.get('credit_amount'),
            request.form.get('credit_sub_subject'),
            request.form.get('description'),
            journal_id,
            tenant_id
        ))
        
        if hasattr(conn, 'commit'):
            conn.commit()
        
        conn.close()
        
        flash('仕訳を更新しました', 'success')
        return redirect(url_for('journal.detail', journal_id=journal_id))
        
    except Exception as e:
        flash(f'更新エラー: {str(e)}', 'error')
        return redirect(request.url)


@bp.route('/<int:journal_id>/confirm', methods=['POST'])
@require_roles(['system_admin', 'tenant_admin', 'admin'])
def confirm(journal_id):
    """仕訳確認"""
    tenant_id = session.get('tenant_id')
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, '''
            UPDATE "T_仕訳"
            SET 確認済みフラグ = 1
            WHERE id = %s AND tenant_id = %s
        ''')
        cur.execute(sql, (journal_id, tenant_id))
        
        if hasattr(conn, 'commit'):
            conn.commit()
        
        conn.close()
        
        flash('仕訳を確認済みにしました', 'success')
        
    except Exception as e:
        flash(f'確認エラー: {str(e)}', 'error')
    
    return redirect(url_for('journal.detail', journal_id=journal_id))


@bp.route('/<int:journal_id>/delete', methods=['POST'])
@require_roles(['system_admin', 'tenant_admin', 'admin'])
def delete(journal_id):
    """仕訳削除"""
    tenant_id = session.get('tenant_id')
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, 'DELETE FROM "T_仕訳" WHERE id = %s AND tenant_id = %s')
        cur.execute(sql, (journal_id, tenant_id))
        
        if hasattr(conn, 'commit'):
            conn.commit()
        
        conn.close()
        
        flash('仕訳を削除しました', 'success')
        
    except Exception as e:
        flash(f'削除エラー: {str(e)}', 'error')
    
    return redirect(url_for('journal.index'))
