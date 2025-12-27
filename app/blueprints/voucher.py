# -*- coding: utf-8 -*-
"""
証憑管理Blueprint
レシート・領収書のアップロード、OCR処理、一覧表示
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from ..utils import get_db, _sql
from ..utils.decorators import require_roles
from ..utils.ocr import process_receipt_image, save_uploaded_file

bp = Blueprint('voucher', __name__, url_prefix='/voucher')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def allowed_file(filename):
    """アップロード可能なファイル形式かチェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
@require_roles(['system_admin', 'tenant_admin', 'admin', 'employee'])
def index():
    """証憑一覧"""
    tenant_id = session.get('tenant_id')
    if not tenant_id:
        flash('テナントが選択されていません', 'error')
        return redirect(url_for('auth.index'))
    
    conn = get_db()
    cur = conn.cursor()
    
    # 証憑一覧を取得
    sql = _sql(conn, '''
        SELECT 
            v.id,
            v.日付,
            v.金額,
            v.摘要,
            v.電話番号,
            v.住所,
            v.ステータス,
            v.created_at,
            u.name as uploaded_by_name
        FROM "T_証憑" v
        LEFT JOIN "T_従業員" u ON v.uploaded_by = u.id
        WHERE v.tenant_id = %s
        ORDER BY v.created_at DESC
    ''')
    cur.execute(sql, (tenant_id,))
    
    if hasattr(cur, 'fetchall'):
        vouchers = cur.fetchall()
    else:
        vouchers = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    return render_template('voucher_list.html', vouchers=vouchers)


@bp.route('/upload', methods=['GET', 'POST'])
@require_roles(['system_admin', 'tenant_admin', 'admin', 'employee'])
def upload():
    """証憑アップロード"""
    if request.method == 'GET':
        return render_template('voucher_upload.html')
    
    tenant_id = session.get('tenant_id')
    user_id = session.get('user_id')
    
    if not tenant_id or not user_id:
        flash('セッション情報が不正です', 'error')
        return redirect(url_for('auth.index'))
    
    # ファイルチェック
    if 'file' not in request.files:
        flash('ファイルが選択されていません', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('ファイルが選択されていません', 'error')
        return redirect(request.url)
    
    if not allowed_file(file.filename):
        flash('許可されていないファイル形式です', 'error')
        return redirect(request.url)
    
    try:
        # ファイルを保存
        filepath = save_uploaded_file(file)
        
        # OCR処理
        ocr_result = process_receipt_image(filepath)
        
        # データベースに保存
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, '''
            INSERT INTO "T_証憑" (
                tenant_id,
                uploaded_by,
                画像パス,
                OCR結果_生データ,
                電話番号,
                住所,
                金額,
                日付,
                ステータス
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''')
        
        # 電話番号と住所は最初の1件を使用
        phone = ocr_result['phone_numbers'][0] if ocr_result['phone_numbers'] else None
        address = ocr_result['addresses'][0] if ocr_result['addresses'] else None
        
        cur.execute(sql, (
            tenant_id,
            user_id,
            filepath,
            ocr_result['raw_text'],
            phone,
            address,
            ocr_result['amount'],
            ocr_result['date'],
            'pending'
        ))
        
        if hasattr(conn, 'commit'):
            conn.commit()
        
        conn.close()
        
        flash('証憑をアップロードしました', 'success')
        return redirect(url_for('voucher.index'))
        
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
        return redirect(request.url)


@bp.route('/<int:voucher_id>')
@require_roles(['system_admin', 'tenant_admin', 'admin', 'employee'])
def detail(voucher_id):
    """証憑詳細"""
    tenant_id = session.get('tenant_id')
    
    conn = get_db()
    cur = conn.cursor()
    
    sql = _sql(conn, '''
        SELECT 
            v.*,
            u.name as uploaded_by_name
        FROM "T_証憑" v
        LEFT JOIN "T_従業員" u ON v.uploaded_by = u.id
        WHERE v.id = %s AND v.tenant_id = %s
    ''')
    cur.execute(sql, (voucher_id, tenant_id))
    
    voucher = cur.fetchone()
    conn.close()
    
    if not voucher:
        flash('証憑が見つかりません', 'error')
        return redirect(url_for('voucher.index'))
    
    return render_template('voucher_detail.html', voucher=voucher)


@bp.route('/<int:voucher_id>/edit', methods=['GET', 'POST'])
@require_roles(['system_admin', 'tenant_admin', 'admin'])
def edit(voucher_id):
    """証憑編集"""
    tenant_id = session.get('tenant_id')
    
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == 'GET':
        sql = _sql(conn, '''
            SELECT * FROM "T_証憑"
            WHERE id = %s AND tenant_id = %s
        ''')
        cur.execute(sql, (voucher_id, tenant_id))
        voucher = cur.fetchone()
        conn.close()
        
        if not voucher:
            flash('証憑が見つかりません', 'error')
            return redirect(url_for('voucher.index'))
        
        return render_template('voucher_edit.html', voucher=voucher)
    
    # POST: 更新処理
    try:
        sql = _sql(conn, '''
            UPDATE "T_証憑"
            SET 
                電話番号 = %s,
                住所 = %s,
                金額 = %s,
                日付 = %s,
                摘要 = %s,
                ステータス = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND tenant_id = %s
        ''')
        
        cur.execute(sql, (
            request.form.get('phone'),
            request.form.get('address'),
            request.form.get('amount'),
            request.form.get('date'),
            request.form.get('description'),
            request.form.get('status', 'pending'),
            voucher_id,
            tenant_id
        ))
        
        if hasattr(conn, 'commit'):
            conn.commit()
        
        conn.close()
        
        flash('証憑を更新しました', 'success')
        return redirect(url_for('voucher.detail', voucher_id=voucher_id))
        
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
        return redirect(request.url)


@bp.route('/<int:voucher_id>/delete', methods=['POST'])
@require_roles(['system_admin', 'tenant_admin', 'admin'])
def delete(voucher_id):
    """証憑削除"""
    tenant_id = session.get('tenant_id')
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # ファイルパスを取得
        sql = _sql(conn, 'SELECT 画像パス FROM "T_証憑" WHERE id = %s AND tenant_id = %s')
        cur.execute(sql, (voucher_id, tenant_id))
        row = cur.fetchone()
        
        if row:
            filepath = row[0] if isinstance(row, tuple) else row['画像パス']
            
            # データベースから削除
            sql = _sql(conn, 'DELETE FROM "T_証憑" WHERE id = %s AND tenant_id = %s')
            cur.execute(sql, (voucher_id, tenant_id))
            
            if hasattr(conn, 'commit'):
                conn.commit()
            
            # ファイルを削除
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            
            flash('証憑を削除しました', 'success')
        else:
            flash('証憑が見つかりません', 'error')
        
        conn.close()
        
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('voucher.index'))
