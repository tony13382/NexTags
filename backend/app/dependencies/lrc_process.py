from anthropic import Anthropic
from config import ANTHROPIC_TOKEN
from app.dependencies.logger import logger


client = Anthropic(
    api_key=ANTHROPIC_TOKEN
)



def call_anthropic_api(prompts):
    """呼叫 Anthropic API"""
    message = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4096,
        temperature=0,
        messages=prompts,
    )
    return message.content[0].text


def log_lrc_preview(lrc_text, prefix=""):
    """記錄歌詞預覽"""
    preview_lines = lrc_text.split("\n")[0:3]
    logger.info(f"{prefix}{preview_lines}")


def lrc_process(lrc: str) -> str:
    """處理歌詞文本"""
    print("正在處理歌詞文本")
    
    if not lrc:
        return ""

    prompts = [
        {"role": "user", "content": """\
你是一個歌詞文本整理助手，工作目標是將歌詞的文本進行整理，直接輸出整理後的歌詞文本，無需添加說明與助詞，整理規則如下：
1. 確認時間格式為 [00:00.00]，如果出現如 [00:00.123] 則直接去除多餘的數字變成 [00:00.12]

2. 如果歌詞為簡體字則轉為繁體（每行處理）
eg. 
[00:00.00]这是一个简单的范例
to:
[00:00.00]這是一個簡單的範例

3. 如果出現任何非中文語言歌詞則在下方加入中文翻譯，翻譯後的文本應該與原文對應，並且在原文下方加上翻譯（每行處理）
eg. 
[00:00.00]This is a simple example
to:
[00:00.00]This is a simple example
[00:00.00]這是一個簡單的範例

eg. 
[00:00.00]이것은 간단한 예입니다
to:
[00:00.00]이것은 간단한 예입니다
[00:00.00]這是一個簡單的範例

現在我需要轉換的文本如下：
    """},
        {"role": "user", "content": lrc},
    ]
    
    log_lrc_preview(lrc)
    
    processed_content = call_anthropic_api(prompts)
    
    log_lrc_preview(processed_content)
    
    return processed_content
