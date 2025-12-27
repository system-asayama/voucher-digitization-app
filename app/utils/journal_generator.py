# -*- coding: utf-8 -*-
"""
仕訳自動生成ユーティリティ
証憑情報から仕訳を自動生成
"""

from typing import Dict, Optional, List, Tuple
import re


# 勘定科目マスタ（簡易版）
ACCOUNT_SUBJECTS = {
    # 資産
    '現金': {'type': '資産', 'category': '流動資産'},
    '普通預金': {'type': '資産', 'category': '流動資産'},
    '当座預金': {'type': '資産', 'category': '流動資産'},
    '受取手形': {'type': '資産', 'category': '流動資産'},
    '売掛金': {'type': '資産', 'category': '流動資産'},
    '前払金': {'type': '資産', 'category': '流動資産'},
    '仮払金': {'type': '資産', 'category': '流動資産'},
    '貸付金': {'type': '資産', 'category': '流動資産'},
    '未収入金': {'type': '資産', 'category': '流動資産'},
    '商品': {'type': '資産', 'category': '流動資産'},
    '建物': {'type': '資産', 'category': '固定資産'},
    '車両運搬具': {'type': '資産', 'category': '固定資産'},
    '工具器具備品': {'type': '資産', 'category': '固定資産'},
    '土地': {'type': '資産', 'category': '固定資産'},
    
    # 負債
    '買掛金': {'type': '負債', 'category': '流動負債'},
    '支払手形': {'type': '負債', 'category': '流動負債'},
    '短期借入金': {'type': '負債', 'category': '流動負債'},
    '未払金': {'type': '負債', 'category': '流動負債'},
    '未払費用': {'type': '負債', 'category': '流動負債'},
    '前受金': {'type': '負債', 'category': '流動負債'},
    '預り金': {'type': '負債', 'category': '流動負債'},
    '仮受金': {'type': '負債', 'category': '流動負債'},
    '長期借入金': {'type': '負債', 'category': '固定負債'},
    
    # 純資産
    '資本金': {'type': '純資産', 'category': '資本'},
    '利益剰余金': {'type': '純資産', 'category': '剰余金'},
    
    # 収益
    '売上高': {'type': '収益', 'category': '営業収益'},
    '受取利息': {'type': '収益', 'category': '営業外収益'},
    '雑収入': {'type': '収益', 'category': '営業外収益'},
    
    # 費用
    '仕入高': {'type': '費用', 'category': '売上原価'},
    '給料手当': {'type': '費用', 'category': '販売費及び一般管理費'},
    '法定福利費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '福利厚生費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '旅費交通費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '通信費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '消耗品費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '水道光熱費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '地代家賃': {'type': '費用', 'category': '販売費及び一般管理費'},
    '支払手数料': {'type': '費用', 'category': '販売費及び一般管理費'},
    '支払保険料': {'type': '費用', 'category': '販売費及び一般管理費'},
    '租税公課': {'type': '費用', 'category': '販売費及び一般管理費'},
    '減価償却費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '広告宣伝費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '接待交際費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '会議費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '新聞図書費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '修繕費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '車両費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '雑費': {'type': '費用', 'category': '販売費及び一般管理費'},
    '支払利息': {'type': '費用', 'category': '営業外費用'},
}


# キーワードベースの勘定科目推定ルール
KEYWORD_RULES = {
    # 交通費関連
    '旅費交通費': ['タクシー', 'JR', '電車', '新幹線', 'バス', '航空', 'ANA', 'JAL', 'ガソリン', 'ETC', '高速', '駐車'],
    
    # 通信費関連
    '通信費': ['携帯', 'スマホ', 'docomo', 'au', 'SoftBank', '電話', 'インターネット', 'プロバイダ', '郵便', '宅配'],
    
    # 消耗品費関連
    '消耗品費': ['文房具', '事務用品', 'コピー用紙', 'インク', 'トナー', '電池', 'USB', '文具'],
    
    # 水道光熱費関連
    '水道光熱費': ['電気', '水道', 'ガス', '東京電力', '東京ガス'],
    
    # 地代家賃関連
    '地代家賃': ['家賃', '賃料', '駐車場', '倉庫', '事務所'],
    
    # 広告宣伝費関連
    '広告宣伝費': ['広告', '宣伝', 'チラシ', 'ポスター', 'Google', 'Facebook', 'Instagram', 'Twitter', 'YouTube'],
    
    # 接待交際費関連
    '接待交際費': ['飲食', '居酒屋', 'レストラン', '食事', '接待', '贈答', 'ギフト'],
    
    # 会議費関連
    '会議費': ['会議', 'カフェ', 'スターバックス', 'ドトール', '喫茶'],
    
    # 新聞図書費関連
    '新聞図書費': ['書籍', '本', '雑誌', '新聞', 'Amazon', '書店'],
    
    # 修繕費関連
    '修繕費': ['修理', '修繕', 'メンテナンス', '保守'],
    
    # 車両費関連
    '車両費': ['車検', '自動車', '洗車', 'オイル', 'タイヤ'],
    
    # 支払手数料関連
    '支払手数料': ['手数料', '振込', '銀行', '決済', 'クレジット'],
    
    # 支払保険料関連
    '支払保険料': ['保険', '損保', '生命保険', '火災保険', '自動車保険'],
    
    # 租税公課関連
    '租税公課': ['税金', '印紙', '登録', '免許', '自動車税', '固定資産税'],
}


def estimate_account_subject(description: str, amount: float, company_name: Optional[str] = None) -> str:
    """
    摘要と金額から勘定科目を推定
    
    Args:
        description: 摘要（説明文）
        amount: 金額
        company_name: 会社名（任意）
    
    Returns:
        推定された勘定科目
    """
    if not description:
        return '雑費'
    
    # キーワードマッチング
    for subject, keywords in KEYWORD_RULES.items():
        for keyword in keywords:
            if keyword in description:
                return subject
    
    # 金額による推定（簡易版）
    if amount >= 100000:
        # 高額な場合は固定資産や仕入の可能性
        if '購入' in description or '買' in description:
            return '仕入高'
    
    # デフォルト
    return '雑費'


def generate_journal_entry(
    voucher_data: Dict,
    company_data: Optional[Dict] = None,
    payment_method: str = '現金'
) -> Dict:
    """
    証憑データから仕訳を自動生成
    
    Args:
        voucher_data: 証憑データ
        company_data: 企業情報データ（任意）
        payment_method: 支払方法（現金、普通預金など）
    
    Returns:
        仕訳データ
    """
    # 金額
    amount = voucher_data.get('金額', 0)
    if not amount:
        amount = 0
    
    # 摘要
    description = voucher_data.get('摘要', '')
    company_name = company_data.get('会社名', '') if company_data else ''
    
    # 勘定科目の推定
    expense_subject = estimate_account_subject(description, amount, company_name)
    
    # 仕訳の生成（借方：費用、貸方：現金/預金）
    journal_entry = {
        '日付': voucher_data.get('日付'),
        '借方勘定科目': expense_subject,
        '借方金額': amount,
        '借方補助科目': company_name if company_name else None,
        '貸方勘定科目': payment_method,
        '貸方金額': amount,
        '貸方補助科目': None,
        '摘要': description or f"{company_name} {expense_subject}" if company_name else expense_subject,
        '自動生成フラグ': 1,
        '確認済みフラグ': 0,
    }
    
    return journal_entry


def validate_journal_entry(journal_entry: Dict) -> Tuple[bool, List[str]]:
    """
    仕訳データの妥当性をチェック
    
    Args:
        journal_entry: 仕訳データ
    
    Returns:
        (妥当性, エラーメッセージのリスト)
    """
    errors = []
    
    # 必須項目チェック
    required_fields = ['日付', '借方勘定科目', '借方金額', '貸方勘定科目', '貸方金額']
    for field in required_fields:
        if not journal_entry.get(field):
            errors.append(f'{field}が設定されていません')
    
    # 金額の一致チェック
    debit_amount = journal_entry.get('借方金額', 0)
    credit_amount = journal_entry.get('貸方金額', 0)
    
    if debit_amount != credit_amount:
        errors.append(f'借方金額({debit_amount})と貸方金額({credit_amount})が一致しません')
    
    # 勘定科目の存在チェック
    debit_subject = journal_entry.get('借方勘定科目')
    credit_subject = journal_entry.get('貸方勘定科目')
    
    if debit_subject and debit_subject not in ACCOUNT_SUBJECTS:
        errors.append(f'借方勘定科目「{debit_subject}」が勘定科目マスタに存在しません')
    
    if credit_subject and credit_subject not in ACCOUNT_SUBJECTS:
        errors.append(f'貸方勘定科目「{credit_subject}」が勘定科目マスタに存在しません')
    
    return len(errors) == 0, errors


def get_account_subject_list() -> List[str]:
    """
    勘定科目リストを取得
    
    Returns:
        勘定科目名のリスト
    """
    return list(ACCOUNT_SUBJECTS.keys())


def get_account_subjects_by_type(account_type: str) -> List[str]:
    """
    種類別の勘定科目リストを取得
    
    Args:
        account_type: 勘定科目の種類（資産、負債、純資産、収益、費用）
    
    Returns:
        勘定科目名のリスト
    """
    return [
        subject for subject, info in ACCOUNT_SUBJECTS.items()
        if info['type'] == account_type
    ]


def suggest_payment_method(voucher_data: Dict) -> str:
    """
    証憑データから支払方法を推定
    
    Args:
        voucher_data: 証憑データ
    
    Returns:
        推定された支払方法
    """
    description = voucher_data.get('摘要', '').lower()
    
    # クレジットカード
    if 'クレジット' in description or 'カード' in description or 'credit' in description:
        return '未払金'
    
    # 銀行振込
    if '振込' in description or '振り込み' in description or '口座' in description:
        return '普通預金'
    
    # デフォルトは現金
    return '現金'


def batch_generate_journal_entries(
    vouchers: List[Dict],
    companies: Dict[int, Dict],
    default_payment_method: str = '現金'
) -> List[Dict]:
    """
    複数の証憑から一括で仕訳を生成
    
    Args:
        vouchers: 証憑データのリスト
        companies: 企業情報の辞書（企業ID -> 企業データ）
        default_payment_method: デフォルトの支払方法
    
    Returns:
        仕訳データのリスト
    """
    journal_entries = []
    
    for voucher in vouchers:
        # 企業情報を取得
        company_id = voucher.get('企業情報ID')
        company_data = companies.get(company_id) if company_id else None
        
        # 支払方法を推定
        payment_method = suggest_payment_method(voucher)
        if not payment_method:
            payment_method = default_payment_method
        
        # 仕訳を生成
        journal_entry = generate_journal_entry(voucher, company_data, payment_method)
        journal_entry['証憑ID'] = voucher.get('id')
        journal_entry['企業情報ID'] = company_id
        
        journal_entries.append(journal_entry)
    
    return journal_entries
