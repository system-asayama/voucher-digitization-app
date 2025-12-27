# -*- coding: utf-8 -*-
"""
AI統合ヘルパー
Gemini 1.5 Flash、GPT-4o-mini、GPT-4oの3モデルに対応
"""

import os
from typing import Dict, Optional, List
from sqlalchemy.orm import Session


def get_ai_settings(db: Session, tenant_id: int) -> Dict[str, str]:
    """
    テナントのAI設定を取得
    
    Args:
        db: データベースセッション
        tenant_id: テナントID
    
    Returns:
        AI設定の辞書
    """
    from ..utils.db import T_テナント
    
    tenant = db.query(T_テナント).filter(T_テナント.id == tenant_id).first()
    
    if not tenant:
        return {
            'ai_model': 'gemini-1.5-flash',  # デフォルト
            'openai_api_key': None,
            'google_api_key': None,
            'anthropic_api_key': None,
        }
    
    return {
        'ai_model': tenant.ai_model or 'gemini-1.5-flash',
        'openai_api_key': tenant.openai_api_key,
        'google_api_key': tenant.google_api_key,
        'anthropic_api_key': tenant.anthropic_api_key,
    }


def call_ai(prompt: str, ai_model: str, api_keys: Dict[str, str]) -> str:
    """
    AIモデルを呼び出してテキスト生成
    
    Args:
        prompt: プロンプト
        ai_model: AIモデル名（'gemini-1.5-flash', 'gpt-4o-mini', 'gpt-4o'）
        api_keys: APIキーの辞書
    
    Returns:
        AI応答テキスト
    """
    if ai_model == 'gemini-1.5-flash':
        return call_gemini(prompt, api_keys.get('google_api_key'))
    elif ai_model == 'gpt-4o-mini':
        return call_openai(prompt, 'gpt-4o-mini', api_keys.get('openai_api_key'))
    elif ai_model == 'gpt-4o':
        return call_openai(prompt, 'gpt-4o', api_keys.get('openai_api_key'))
    else:
        raise ValueError(f"サポートされていないAIモデル: {ai_model}")


def call_gemini(prompt: str, api_key: Optional[str]) -> str:
    """
    Google Gemini APIを呼び出し
    
    Args:
        prompt: プロンプト
        api_key: Google API Key
    
    Returns:
        AI応答テキスト
    """
    if not api_key:
        raise ValueError("Google API Keyが設定されていません")
    
    import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    response = model.generate_content(prompt)
    return response.text


def call_openai(prompt: str, model: str, api_key: Optional[str]) -> str:
    """
    OpenAI APIを呼び出し
    
    Args:
        prompt: プロンプト
        model: モデル名（'gpt-4o-mini' or 'gpt-4o'）
        api_key: OpenAI API Key
    
    Returns:
        AI応答テキスト
    """
    if not api_key:
        raise ValueError("OpenAI API Keyが設定されていません")
    
    from openai import OpenAI
    
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "あなたは会計処理の専門家です。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )
    
    return response.choices[0].message.content


def correct_ocr_text(ocr_text: str, ai_model: str, api_keys: Dict[str, str]) -> str:
    """
    OCR結果をAIで補正
    
    Args:
        ocr_text: OCRで抽出されたテキスト
        ai_model: 使用するAIモデル
        api_keys: APIキーの辞書
    
    Returns:
        補正されたテキスト
    """
    prompt = f"""
以下はレシート・領収書からOCRで抽出されたテキストです。
OCRの誤認識を修正し、正確なテキストに補正してください。

【補正ルール】
1. 「林式会社」→「株式会社」
2. 数字の「0」と英字の「O」を区別
3. 「1」と「l」（エル）を区別
4. 住所の番地の誤認識を修正
5. 会社名の略称を正式名称に変換（㈱→株式会社、(株)→株式会社）

【OCRテキスト】
{ocr_text}

【補正後のテキスト】
補正後のテキストのみを出力してください。説明は不要です。
"""
    
    try:
        return call_ai(prompt, ai_model, api_keys)
    except Exception as e:
        print(f"AI補正エラー: {e}")
        return ocr_text  # エラー時は元のテキストを返す


def estimate_account_subject_with_ai(
    ocr_text: str,
    company_name: Optional[str],
    amount: Optional[float],
    ai_model: str,
    api_keys: Dict[str, str]
) -> Dict[str, str]:
    """
    AIを使用して勘定科目を推定
    
    Args:
        ocr_text: OCRで抽出されたテキスト
        company_name: 会社名
        amount: 金額
        ai_model: 使用するAIモデル
        api_keys: APIキーの辞書
    
    Returns:
        推定結果の辞書（勘定科目、摘要）
    """
    prompt = f"""
以下のレシート・領収書情報から、適切な勘定科目を推定してください。

【情報】
会社名: {company_name or '不明'}
金額: {amount or '不明'}円
レシート内容:
{ocr_text}

【利用可能な勘定科目】
- 旅費交通費（電車、バス、タクシー、新幹線、飛行機、ガソリン、駐車場など）
- 通信費（携帯電話、インターネット、郵便、宅配便など）
- 消耗品費（文房具、事務用品、日用品など）
- 水道光熱費（電気、ガス、水道など）
- 地代家賃（家賃、駐車場代、倉庫代など）
- 広告宣伝費（広告、SNS広告、チラシなど）
- 接待交際費（飲食、贈答、ゴルフなど）
- 会議費（会議室、飲食（少人数）など）
- 福利厚生費（社員の慰安、健康診断など）
- 研修費（セミナー、書籍、eラーニングなど）
- 支払手数料（振込手数料、各種手数料など）
- 租税公課（印紙、自動車税、固定資産税など）
- 修繕費（修理、メンテナンスなど）
- 保険料（損害保険、自動車保険など）
- 雑費（その他）

【出力形式】
以下のJSON形式で出力してください。
{{
  "account_subject": "勘定科目名",
  "description": "摘要（具体的な内容）"
}}

JSONのみを出力し、説明は不要です。
"""
    
    try:
        response = call_ai(prompt, ai_model, api_keys)
        
        # JSON部分を抽出
        import json
        import re
        
        # JSONブロックを抽出（```json ... ``` または { ... }）
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response
        
        result = json.loads(json_str)
        return {
            'account_subject': result.get('account_subject', '雑費'),
            'description': result.get('description', ''),
        }
    except Exception as e:
        print(f"AI勘定科目推定エラー: {e}")
        return {
            'account_subject': '雑費',
            'description': '',
        }


def normalize_company_name_with_ai(
    company_name: str,
    ai_model: str,
    api_keys: Dict[str, str]
) -> str:
    """
    AIを使用して会社名を正規化
    
    Args:
        company_name: 会社名
        ai_model: 使用するAIモデル
        api_keys: APIキーの辞書
    
    Returns:
        正規化された会社名
    """
    prompt = f"""
以下の会社名を正式名称に正規化してください。

【会社名】
{company_name}

【正規化ルール】
1. 略称を正式名称に変換（㈱→株式会社、(株)→株式会社、(有)→有限会社など）
2. 前株・後株を正しい位置に配置
3. カタカナ・英字の表記ゆれを統一
4. スペースや記号を適切に処理

【出力】
正規化された会社名のみを出力してください。説明は不要です。
"""
    
    try:
        return call_ai(prompt, ai_model, api_keys).strip()
    except Exception as e:
        print(f"AI会社名正規化エラー: {e}")
        return company_name


def select_best_company_from_candidates(
    candidates: List[Dict],
    ocr_address: Optional[str],
    ai_model: str,
    api_keys: Dict[str, str]
) -> Optional[Dict]:
    """
    複数の企業候補から最適な企業をAIで選択
    
    Args:
        candidates: 企業候補のリスト
        ocr_address: OCRで抽出された住所
        ai_model: 使用するAIモデル
        api_keys: APIキーの辞書
    
    Returns:
        選択された企業情報
    """
    if not candidates:
        return None
    
    if len(candidates) == 1:
        return candidates[0]
    
    # 候補を文字列化
    candidates_text = "\n".join([
        f"{i+1}. {c.get('name', '不明')} - {c.get('address', '不明')}"
        for i, c in enumerate(candidates)
    ])
    
    prompt = f"""
以下の企業候補から、OCRで抽出された住所に最も一致する企業を選択してください。

【OCRで抽出された住所】
{ocr_address or '不明'}

【企業候補】
{candidates_text}

【出力】
最も一致する企業の番号のみを出力してください（1, 2, 3...）。
説明は不要です。
"""
    
    try:
        response = call_ai(prompt, ai_model, api_keys).strip()
        # 数字のみを抽出
        import re
        match = re.search(r'\d+', response)
        if match:
            index = int(match.group(0)) - 1
            if 0 <= index < len(candidates):
                return candidates[index]
    except Exception as e:
        print(f"AI企業選択エラー: {e}")
    
    # エラー時は最初の候補を返す
    return candidates[0]


def get_ai_model_info(model_name: str) -> Dict[str, any]:
    """
    AIモデルの情報を取得
    
    Args:
        model_name: モデル名
    
    Returns:
        モデル情報の辞書
    """
    models = {
        'gemini-1.5-flash': {
            'name': 'Gemini 1.5 Flash',
            'provider': 'Google',
            'cost_per_transaction': 0.17,  # 円
            'description': '最安値、高速処理',
        },
        'gpt-4o-mini': {
            'name': 'GPT-4o mini',
            'provider': 'OpenAI',
            'cost_per_transaction': 0.19,  # 円
            'description': 'コスパ良好、高精度',
        },
        'gpt-4o': {
            'name': 'GPT-4o',
            'provider': 'OpenAI',
            'cost_per_transaction': 0.83,  # 円
            'description': '最高精度',
        },
    }
    
    return models.get(model_name, {})
