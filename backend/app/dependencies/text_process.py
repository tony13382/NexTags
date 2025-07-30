from pypinyin import pinyin, Style

def convertPinyin(text):
    """將中文文字轉換為拼音"""
    result = pinyin(text, style=Style.NORMAL)
    return "".join([item[0] for item in result])