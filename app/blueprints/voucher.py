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
from ..utils.nta_api import search_company_by_ocr_data
from ..utils.ai_helper import get_ai_settings, correct_ocr_text, normalize_company_name_with_ai, select_best_company_from_candidates

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
        
        # AI設定を取得
        conn_temp = get_db()
        cur_temp = conn_temp.cursor()
        ai_settings = {'ai_model': 'gemini-1.5-flash'}  # デフォルト
        api_keys = {}
        
        try:
            cur_temp.execute(_sql(conn_temp, 'SELECT ai_model, openai_api_key, google_api_key, anthropic_api_key FROM "T_テナント" WHERE id = %s'), (tenant_id,))
            tenant_settings = cur_temp.fetchone()
            if tenant_settings:
                ai_settings['ai_model'] = tenant_settings[0] or 'gemini-1.5-flash'
                api_keys = {
                    'openai_api_key': tenant_settings[1],
                    'google_api_key': tenant_settings[2],
                    'anthropic_api_key': tenant_settings[3],
                }
        except Exception as e:
            print(f"AI設定取得エラー: {e}")
        finally:
            conn_temp.close()
        
        # AIでOCR結果を補正
        try:
            if api_keys.get('google_api_key') or api_keys.get('openai_api_key'):
                corrected_text = correct_ocr_text(
                    ocr_result.get('full_text', ''),
                    ai_settings['ai_model'],
                    api_keys
                )
                # 補正後のテキストを再解析
                from ..utils.ocr import extract_phone_numbers, extract_addresses, extract_company_name
                ocr_result['phone_numbers'] = extract_phone_numbers(corrected_text)
                ocr_result['addresses'] = extract_addresses(corrected_text)
                ocr_result['company_name'] = extract_company_name(corrected_text)
        except Exception as e:
            print(f"AI補正エラー: {e}")
        
        # 電話番号と住所は最初の1件を使用
        phone = ocr_result['phone_numbers'][0] if ocr_result['phone_numbers'] else None
        address = ocr_result['addresses'][0] if ocr_result['addresses'] else None
        company_name = ocr_result.get('company_name')
        
        # AIで会社名を正規化
        if company_name and (api_keys.get('google_api_key') or api_keys.get('openai_api_key')):
            try:
                company_name = normalize_company_name_with_ai(
                    company_name,
                    ai_settings['ai_model'],
                    api_keys
                )
            except Exception as e:
                print(f"AI会社名正規化エラー: {e}")
        
        # OCR結果から企業情報を自動検索
        company_id = None
        invoice_number = None
        corporate_number = None
        
        if company_name or address or phone:
            companies = search_company_by_ocr_data(
                company_name=company_name,
                address=address,
                phone_number=phone
            )
            
            if companies:
                # 最初の候補を使用
                company_info = companies[0]
                invoice_number = company_info.get('インボイス登録番号')
                corporate_number = company_info.get('法人番号')
                
                # 企業情報をデータベースに保存（既存の場合は更新）
                conn = get_db()
                cur = conn.cursor()
                
                # 既存の企業情報をチェック
                check_sql = _sql(conn, '''
                    SELECT id FROM "T_企業情報"
                    WHERE 法人番号 = %s OR インボイス登録番号 = %s
                ''')
                cur.execute(check_sql, (corporate_number, invoice_number))
                existing = cur.fetchone()
                
                if existing:
                    company_id = existing[0] if isinstance(existing, tuple) else existing['id']
                else:
                    # 新規企業情報を登録
                    insert_company_sql = _sql(conn, '''
                        INSERT INTO "T_企業情報" (
                            tenant_id,
                            法人番号,
                            インボイス登録番号,
                            会社名,
                            会社名カナ,
                            郵便番号,
                            住所,
                            都道府県,
                            市区町村,
                            番地,
                            インボイス登録有無,
                            インボイス登録日,
                            法人種別
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''')
                    
                    cur.execute(insert_company_sql, (
                        tenant_id,
                        company_info.get('法人番号'),
                        company_info.get('インボイス登録番号'),
                        company_info.get('会社名'),
                        company_info.get('会社名カナ'),
                        company_info.get('郵便番号'),
                        company_info.get('住所'),
                        company_info.get('都道府県'),
                        company_info.get('市区町村'),
                        company_info.get('番地'),
                        company_info.get('インボイス登録有無', 0),
                        company_info.get('インボイス登録日'),
                        company_info.get('法人種別')
                    ))
                    
                    if hasattr(conn, 'commit'):
                        conn.commit()
                    
                    # 挿入されたIDを取得
                    company_id = cur.lastrowid
                
                conn.close()
        
        # データベースに証憑情報を保存
        conn = get_db()
        cur = conn.cursor()
        
        sql = _sql(conn, '''
            INSERT INTO "T_証憑" (
                tenant_id,
                uploaded_by,
                company_id,
                画像パス,
                OCR結果_生データ,
                電話番号,
                住所,
                金額,
                日付,
                ステータス
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''')
        
        cur.execute(sql, (
            tenant_id,
            user_id,
            company_id,
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
