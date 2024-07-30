from tiktoken import get_encoding

from config import CONFIG


class TokenHandler:
    """
    用于计算消息的tokens数量
    """

    def __init__(self, system="", user=""):
        """
        Initializes the TokenHandler object.

        Args:
            system (str): system prompt
            user (str): user prompt
        """
        self.encoder = get_encoding("o200k_base")  # cl100k_base
        self.prompt_tokens = self.count_tokens(system) + self.count_tokens(user)
        self.max_tokens: int = CONFIG.config.max_model_tokens

    def count_tokens(self, text):
        """
        计算指定字符串的tokens数量

        Args:
            text (str): 指定字符串。

        Returns:
            int: tokens数量。
        """
        return len(self.encoder.encode(text, disallowed_special=()))
