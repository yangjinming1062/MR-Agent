from dataclasses import dataclass

from pydantic import BaseModel
from pydantic import Field

from .enums import *


@dataclass
class FilePatchInfo:
    base_file: str | None
    head_file: str | None
    patch: str | None
    filename: str
    tokens: int = -1
    edit_type: EditType = EditType.UNKNOWN
    old_filename: str = None


@dataclass
class LanguageInfo:
    name: str
    files: list[FilePatchInfo]


class CONSTANTS:
    # 模板string
    DIFF_EXAMPLE = """
    我将使用如下的格式来呈现MR的代码差异：
======
## file: 'src/file1.py'

@@ ... @@ def func1():
__new hunk__
12  code line1 that remained unchanged in the MR
13 +new hunk code line2 added in the MR
14  code line3 that remained unchanged in the MR
__old hunk__
 code line1 that remained unchanged in the MR
-old hunk code line2 that was removed in the MR
 code line3 that remained unchanged in the MR

@@ ... @@ def func2():
__new hunk__
...
__old hunk__
...


## file: 'src/file2.py'
...
======
- 在这种格式中，我将每个差异代码块分为“__new hunk__”和“__old hunk__”部分。'__new hunk__'部分包含块的新代码，'__old hunk__''部分包含已删除的旧代码。
- 我还为“__new hunk__”部分添加了行号，以帮助您参考建议中的代码行。这些行号不是实际代码的一部分，仅供参考。
- 代码行以符号（“+”、“-”、“”）作为前缀。“+”符号表示在PR中添加了新代码，“-”符号表示PR中删除了代码，“ ”符号表示代码未更改, 审查应侧重于MR差异中添加的新代码（以“+”开头的行）
- 从代码中引用变量或名称时，请使用回引号（`）而不是单引号（'）。
    """
    USE_FORMATTED_OUTPUT = "你必须严格使用以下YAML格式来回答"
    YAML_FORMAT = "如有必要，每个YAML输出应该采用块标量格式('|-')。确保输出是一个有效的YAML文件。不要在回答中重复提示，不要输出“type”和“description”字段"
    LABEL_OF_MR = "MR类型"
    LABELS = """
  type: array
  description: 适用于合并请求的标签。不要输出括号中的描述。如果没有一个标签与MR相关，则输出一个空数组。
  items:
    type: string
    enum:
      - 修复BUG
      - 新功能
      - 测试
      - 重构
      - 优化
      - 文档
      - 其他
    """
    # 提交消息
    COMMIT_TITLE = "标题"
    COMMIT_BRANCH = "分支"
    COMMIT_DESCRIPTION = "描述"
    COMMIT_MESSAGE = "提交信息"
    # review
    ANALYSIS = "MR 分析"
    THEME = "主题"
    SUMMARY = "总结"
    TESTS = "单元测试"
    FOCUSED = "聚焦"
    ERROR = "错误"
    SCORE = "得分 [0-10]"
    REVIEW_ESTIMATED = "预估审计量 [1-5]"
    MR_FEEDBACK = "MR 反馈"
    GENERAL_SUGGESTIONS = "建议与反馈"
    SECURITY_CONCERNS = "安全问题"
    CODE_SUGGESTIONS = "代码建议"
    RELEVANT_FILE = "相关文件"
    SUGGESTION = "建议"
    EXISTING_CODE = "现有代码"
    RELEVANT_LINE_START = "相关行头"
    RELEVANT_LINE_END = "相关行尾"
    IMPROVED_CODE = "改进代码"
    # describe
    TITLE = "标题"
    DESCRIPTION = "描述"
    MAIN_FILES_WALKTHROUGH = "主要变更文件概览"
    FILENAME = "文件"
    CHANGES_IN_FILE = "文件变化"
    # other
    USER_DESCRIPTION = "用户描述"
    RELEVANT_LINE = "具体位置"


class CommandParams(BaseModel):
    """
    命令通用参数
    """

    publish_labels: bool = Field(True, description="推送标签")
    extra_instructions: str = Field("", alias="e", alias_priority=0, description="附加的prompts")
    ai_temperature: float = Field(0.2, description="模型温度")
    patch_extra_lines: int = Field(0, description="获取提交的代码差异时在代码周围额外附加的代码行数")

    def __str__(self):
        result = ""
        for k, v in self.model_fields.items():
            if v.exclude:
                continue
            title = f"**-{v.alias}|--{k}**" if v.alias else f"**--{k}**"
            if issubclass(v.annotation, Enum):
                _value_range = ", ".join([x.value for x in v.annotation])
                body = f"【默认: {v.default.value}】【可选：{_value_range}】"
            else:
                body = f"【默认: {v.default}】"
            result += f"> {title}: {v.description}{body}\n\n"
        return result

    @classmethod
    def deserialize(cls, data):
        """
        序列化参数（主要是解决alias和列名称任意传递的问题）

        Args:
            data (dict):

        Returns:

        """
        for k, v in cls.model_fields.items():
            if v.alias and v.alias not in data:
                if k in data:
                    data[v.alias] = data[k]
        return cls.model_validate(data)
