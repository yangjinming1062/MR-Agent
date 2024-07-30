import asyncio
import copy
import os.path
import pickle

from jinja2 import Environment
from jinja2 import StrictUndefined

from core import *
from defines import *
from utils import *

# 各种模板种的待替换内容的常量字典
CONSTANTS_DICT = {k: v for k, v in CONSTANTS.__dict__.items() if k.isupper()}


class CommandBase:
    """
    命令基类
    """

    params: CommandParams
    system_template: str
    user_template: str = USER_TEMPLATE

    def __init__(self, git_provider, params, **kwargs):
        """

        Args:
            git_provider (GitProvider): gitlab instance
            params (CommandParams):
        """
        self.params = params
        self.git_provider = git_provider
        self.main_language = get_main_language(self.git_provider.get_languages(), self.git_provider.get_files())
        self.prediction = {}  # key是模型的名称，value是调用结果
        self.variables = {
            "title": self.git_provider.mr.title,
            "branch": self.git_provider.get_mr_branch(),
            "language": self.main_language,
            "extra_instructions": params.extra_instructions,
            "diff": "",  # empty diff for initial calculation
            "description": "",
            "commit_messages_str": "",
        }
        self.variables.update(params.model_dump())
        self.variables.update(CONSTANTS_DICT)
        self.mr_id = self.git_provider.mr_id

    async def run(self):
        """
        命令执行的入口函数（各种命令统一由此调用）

        Returns:
            None
        """
        try:
            await self.generate_prediction()
            for model, prediction in self.prediction.items():
                if data := load_yaml(prediction):
                    self.subclass_run(model, data)
                elif prediction:
                    # 不是预期的结构但是有响应数据也直接添加评论，不能浪费
                    self.git_provider.publish_comment(f"{model}:{prediction}")
        except Exception as e:
            logger.exception(f"Failed: {e=}")

    def subclass_run(self, model, data):
        """
        各子类实现差异化的逻辑

        Args:
            model (str):
            data (dict | list):

        Returns:
            None
        """
        raise NotImplemented

    @call_with_retry
    async def generate_prediction(self):
        """
        调用AI模型预测(响应结果直接存储在self.prediction中)

        Returns:
            None
        """
        if prediction := await self._prediction():
            self.prediction[AiHandler.model] = prediction.strip()

    async def _prediction(self):
        """
        实际调用AI模型生成响应数据的方法

        Returns:
            str: AI预测的字符串。
        """
        try:
            variables = copy.deepcopy(self.variables)
            environment = Environment(undefined=StrictUndefined)
            system_prompt = environment.from_string(self.system_template).render(variables)
            user_prompt = environment.from_string(self.user_template).render(variables)
            # 目前的system_prompt和user_prompt还没有diff信息
            token_handler = TokenHandler(system_prompt, user_prompt)
            variables["diff"] = get_diff(self.git_provider, token_handler, False, self.params.patch_extra_lines)
            variables["description"] = self.git_provider.get_description(token_handler)
            variables["commit_messages_str"] = self.git_provider.get_commit_messages(token_handler)
            # 带上diff信息后的完整prompt
            system_prompt = environment.from_string(self.system_template).render(variables)
            user_prompt = environment.from_string(self.user_template).render(variables)

            logger.debug(f"\nSystem prompt:\n{system_prompt}")
            logger.debug(f"\nUser prompt:\n{user_prompt}")

            if not os.path.exists(f"{AiHandler.model}_response.pkl"):
                response = await AiHandler.chat_completion(
                    temperature=self.params.ai_temperature,
                    system=system_prompt,
                    user=user_prompt,
                )
                # DEBUG的时候使用响应暂存的方式减少不必要的AI调用
                # pickle.dump(response, open(f'{handler.model}_response.pkl', 'wb'))
            else:
                response = pickle.load(open(f"{AiHandler.model}_response.pkl", "rb"))

            logger.debug(f"AI response {AiHandler.model}:\n{response}")

            return response
        except Exception as ex:
            logger.exception(ex)

    @staticmethod
    def get_labels(data):
        """
        获取回答中的标签信息

        Args:
            data:

        Returns:
            list
        """
        types = []
        if CONSTANTS.LABEL_OF_MR in data:
            if isinstance(data[CONSTANTS.LABEL_OF_MR], list):
                types = data[CONSTANTS.LABEL_OF_MR]
            elif isinstance(data[CONSTANTS.LABEL_OF_MR], str):
                types = data[CONSTANTS.LABEL_OF_MR].split(",")
        return types
