from functools import wraps

import yaml

from defines import BAD_EXTENSIONS
from defines import CONSTANTS
from utils import logger


def _parse_code_suggestion(data):
    """
    将dict转换为markdown格式（专门处理代码建议的）。

    Args:
        data (dict): 代码建议

    Returns:
        str: markdown格式字符串
    """
    markdown_text = f"\n\n### **🤖 {CONSTANTS.CODE_SUGGESTIONS}:**\n\n"
    for sub_key, sub_value in data.items():
        if sub_key in {CONSTANTS.EXISTING_CODE, CONSTANTS.IMPROVED_CODE}:
            markdown_text += f"\n  - **{sub_key}:**\n```\n{sub_value}\n\n```"
        else:
            markdown_text += f"\n  - **{sub_key}:** {sub_value}\n"
            markdown_text = markdown_text.rstrip("\n") + "   \n"  # works for gitlab and bitbucker

    markdown_text += "\n"
    return markdown_text


def convert_to_markdown(data):
    """
    将dict转换为markdown格式。

    Args:
        data (dict): 转换前的dict数据

    Returns:
        str: markdown格式字符串
    """
    markdown_text = ""

    emojis = {
        CONSTANTS.THEME: "🎯",
        CONSTANTS.SUMMARY: "📝",
        CONSTANTS.LABEL_OF_MR: "📌",
        CONSTANTS.SCORE: "🏅",
        CONSTANTS.TESTS: "🧪",
        CONSTANTS.ERROR: "❌",
        CONSTANTS.FOCUSED: "✨",
        CONSTANTS.SECURITY_CONCERNS: "🔒",
        CONSTANTS.SUGGESTION: "💡",
        CONSTANTS.REVIEW_ESTIMATED: "⏱️",
    }

    for key, value in data.items():
        if not value:
            continue
        if isinstance(value, dict):
            markdown_text += f"## {key}\n\n"
            markdown_text += convert_to_markdown(value)
        elif isinstance(value, list):
            emoji = emojis.get(key, "")
            if key != CONSTANTS.CODE_SUGGESTIONS:
                markdown_text += f"- {emoji} **{key}:**\n\n"
            for item in value:
                if key == CONSTANTS.CODE_SUGGESTIONS:
                    markdown_text += _parse_code_suggestion(item)
                else:
                    markdown_text += f"  - {item}\n"
        elif value != "n/a":
            emoji = emojis.get(key, "")
            markdown_text += f"- {emoji} **{key}:** {value}\n"
    return markdown_text


def _try_fix_yaml(response_text):
    """
    尝试修复无法加载的yaml字符串

    Args:
        response_text (str):

    Returns:
        dict
    """
    response_text_lines = response_text.split("\n")
    keys = [f"{CONSTANTS.SUGGESTION}:", f"{CONSTANTS.RELEVANT_FILE}:"]

    # first fallback - try to convert 'relevant line: ...' to relevant line: |-\n        ...'
    new_lines = []
    for i, row in enumerate(response_text_lines):
        for k in keys:
            if k in row and "|-" not in row:
                new_lines.append(row.replace(f"{k}", f"{k} |-\n        "))
                break
        else:
            new_lines.append(row)
    try:
        return yaml.safe_load("\n".join(new_lines))
    except:
        logger.info("Failed to parse AI prediction after adding |-\n")

    # second fallback - try to remove last lines
    data = {}
    for i in range(1, len(response_text_lines)):
        try:
            data = yaml.safe_load(
                "\n".join(response_text_lines[:-i]),
            )
            logger.info(f"Successfully parsed AI prediction after removing {i} lines")
            break
        except:
            pass
    return data


def load_yaml(response_text):
    """
    加载yaml格式字符串

    Args:
        response_text (str):

    Returns:
        dict
    """
    response_text = response_text.removeprefix("```yaml").rstrip("`")
    try:
        data = yaml.safe_load(response_text)
    except Exception as e:
        logger.error(f"Failed to parse AI prediction: {e}")
        data = _try_fix_yaml(response_text)
    return data


def clip_tokens(token_handler, text, max_tokens):
    """
    将字符串中的令牌数量裁剪为最大令牌数量(如果超出限制的话)。

    Args:
        token_handler (TokenHandler):
        text (str): 待修建的字符串。
        max_tokens (int): 字符串令牌上限。

    Returns:
        str: 修剪后的字符串。
    """
    if not text:
        return text

    try:
        if (num_input_tokens := token_handler.count_tokens(text)) <= max_tokens:
            return text
        chars_per_token = len(text) / num_input_tokens
        num_output_chars = int(chars_per_token * max_tokens)
        return text[:num_output_chars]
    except Exception as e:
        logger.warning(f"Failed to clip tokens: {e}")
        return text


def call_with_retry(function):
    """
    装饰器: 异常捕获。

    Returns:
        str | None:
    """

    @wraps(function)
    def wrapper(*args, **kwargs):
        for _ in range(3):
            try:
                return function(*args, **kwargs)
            except Exception as ex:
                logger.debug(ex)

    return wrapper


def is_valid_file(filename):
    """
    过滤掉不支持的文件

    Args:
        filename (str): 文件名

    Returns:
        bool: 是否有序
    """
    return filename.split(".")[-1] not in BAD_EXTENSIONS
