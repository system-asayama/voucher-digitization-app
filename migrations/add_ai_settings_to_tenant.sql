-- T_テナントテーブルにAI設定カラムを追加

-- PostgreSQL用
ALTER TABLE "T_テナント" ADD COLUMN IF NOT EXISTS ai_model TEXT DEFAULT 'gemini-1.5-flash';
ALTER TABLE "T_テナント" ADD COLUMN IF NOT EXISTS openai_api_key TEXT;
ALTER TABLE "T_テナント" ADD COLUMN IF NOT EXISTS google_api_key TEXT;
ALTER TABLE "T_テナント" ADD COLUMN IF NOT EXISTS anthropic_api_key TEXT;
