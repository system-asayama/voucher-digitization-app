# -*- coding: utf-8 -*-
"""
OCR処理とデータ抽出ユーティリティ
"""

import re
import os
from typing import Dict, Optional, List
from PIL import Image
import pytesseract


def extract_text_from_image(image_path: str, lang: str = 'jpn') -> str:
    """
    画像からテキストを抽出
    
    Args:
        image_path: 画像ファイルのパス
        lang: OCR言語設定（デフォルト: 'jpn'）
    
    Returns:
        抽出されたテキスト
    """
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=lang)
        return text
    except Exception as e:
        print(f"OCRエラー: {e}")
        return ""


def extract_phone_numbers(text: str) -> List[str]:
    """
    テキストから電話番号を抽出
    
    Args:
        text: 検索対象のテキスト
    
    Returns:
        抽出された電話番号のリスト
    """
    # 日本の電話番号パターン
    patterns = [
        r'\d{2,4}-\d{2,4}-\d{4}',  # 03-1234-5678
        r'\d{3}-\d{3}-\d{4}',      # 090-1234-5678
        r'\(\d{2,4}\)\s*\d{2,4}-\d{4}',  # (03) 1234-5678
        r'\d{10,11}',              # 09012345678
    ]
    
    phone_numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        phone_numbers.extend(matches)
    
    # 重複を削除
    return list(set(phone_numbers))


def extract_addresses(text: str) -> List[str]:
    """
    テキストから住所を抽出
    
    Args:
        text: 検索対象のテキスト
    
    Returns:
        抽出された住所のリスト
    """
    # 日本の住所パターン（都道府県から始まる）
    prefectures = [
        '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
        '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
        '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
        '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
        '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
        '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
        '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
    ]
    
    addresses = []
    lines = text.split('\n')
    
    for line in lines:
        for prefecture in prefectures:
            if prefecture in line:
                # 都道府県を含む行全体を住所として抽出
                cleaned = line.strip()
                if cleaned and len(cleaned) > 5:  # 最低限の長さチェック
                    addresses.append(cleaned)
                    break
    
    return addresses


def extract_postal_code(text: str) -> Optional[str]:
    """
    テキストから郵便番号を抽出
    
    Args:
        text: 検索対象のテキスト
    
    Returns:
        抽出された郵便番号（最初の1件）
    """
    # 郵便番号パターン（〒123-4567 または 123-4567）
    pattern = r'〒?\s*(\d{3}-\d{4})'
    match = re.search(pattern, text)
    
    if match:
        return match.group(1)
    return None


def extract_amount(text: str) -> Optional[float]:
    """
    テキストから金額を抽出
    
    Args:
        text: 検索対象のテキスト
    
    Returns:
        抽出された金額（最大値）
    """
    # 金額パターン（¥1,234 または 1,234円 または 1234）
    patterns = [
        r'¥\s*([\d,]+)',
        r'([\d,]+)\s*円',
        r'合計\s*[：:]\s*([\d,]+)',
        r'小計\s*[：:]\s*([\d,]+)',
    ]
    
    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # カンマを削除して数値に変換
            try:
                amount = float(match.replace(',', ''))
                amounts.append(amount)
            except ValueError:
                continue
    
    # 最大値を返す（通常、合計金額が最大）
    return max(amounts) if amounts else None


def extract_date(text: str) -> Optional[str]:
    """
    テキストから日付を抽出
    
    Args:
        text: 検索対象のテキスト
    
    Returns:
        抽出された日付（YYYY-MM-DD形式）
    """
    # 日付パターン
    patterns = [
        r'(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})',  # 2024年1月1日, 2024/1/1, 2024-1-1
        r'(\d{4})\.(\d{1,2})\.(\d{1,2})',  # 2024.1.1
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            year, month, day = match.groups()
            # YYYY-MM-DD形式に変換
            return f"{year}-{int(month):02d}-{int(day):02d}"
    
    return None


def process_receipt_image(image_path: str) -> Dict[str, any]:
    """
    レシート画像を処理して情報を抽出
    
    Args:
        image_path: 画像ファイルのパス
    
    Returns:
        抽出された情報の辞書
    """
    # OCRでテキスト抽出
    text = extract_text_from_image(image_path)
    
    # 各種情報を抽出
    result = {
        'raw_text': text,
        'phone_numbers': extract_phone_numbers(text),
        'addresses': extract_addresses(text),
        'postal_code': extract_postal_code(text),
        'amount': extract_amount(text),
        'date': extract_date(text),
    }
    
    return result


def save_uploaded_file(file, upload_folder: str = 'uploads') -> str:
    """
    アップロードされたファイルを保存
    
    Args:
        file: アップロードされたファイルオブジェクト
        upload_folder: 保存先フォルダ
    
    Returns:
        保存されたファイルのパス
    """
    os.makedirs(upload_folder, exist_ok=True)
    
    # ファイル名を安全にする
    filename = file.filename
    filepath = os.path.join(upload_folder, filename)
    
    # 同名ファイルがある場合は連番を付ける
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filepath):
        filename = f"{base}_{counter}{ext}"
        filepath = os.path.join(upload_folder, filename)
        counter += 1
    
    file.save(filepath)
    return filepath
