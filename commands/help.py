from ._commands_base import *
from .describe import CommandDescribe
from .describe import CommandDescribeParams
from .labels import CommandLabels
from .review import CommandReview
from .review import CommandReviewParams

ACTIONS_HELP_TEXT = f"""## 使用帮助:\n 
### 命令:\n 
要调用MR-Agent，在comments中添加以下命令之一::\n 
> **{CommandType.Help.value}**: 使用帮助，添加 -<命令> 来查看更多细节。\n
> **{CommandType.Review.value}**: 执行Code Review，配合具体参数完成定制化的Code Review。\n
> **{CommandType.Describe.value}**: 根据MR的内容更新MR的标题和描述。\n
> **{CommandType.Labels.value}**: 根据MR的内容为MR添加标签。\n

>例如: {CommandType.Help.value} -{CommandType.Help.value}
"""


class CommandHelp(CommandBase):

    def __init__(self, git_provider, params, original_params, **kwargs):
        self.args = original_params
        super(CommandHelp, self).__init__(git_provider, params)

    async def run(self):
        comment = ACTIONS_HELP_TEXT
        for command_type in list(CommandType):
            if command_type.value not in self.args:
                continue
            if command_type == CommandType.Help:
                comment += self.get_help_text()
            else:
                comment += get_help_text(CommandType.Review)
        self.git_provider.publish_persistent_comment(comment, initial_header=f"## 使用帮助", update_header=False)

    @staticmethod
    def get_help_text():
        return f"""
### {CommandType.Help.value}参数:\n
> **-{CommandType.Help.value}**: 查看{CommandType.Help.value}命令支持的附加参数（PS：也就是附加本段内容）。\n
> **-{CommandType.Review.value}**: 查看{CommandType.Review.value}命令支持的附加参数。\n
> **-{CommandType.Describe.value}**: 查看{CommandType.Describe.value}命令支持的附加参数。\n
> **-{CommandType.Labels.value}**: 查看{CommandType.Labels.value}命令支持的附加参数。\n
"""


COMMAND_MAP = {
    CommandType.Describe: (CommandDescribe, CommandDescribeParams),
    CommandType.Help: (CommandHelp, CommandParams),
    CommandType.Labels: (CommandLabels, CommandParams),
    CommandType.Review: (CommandReview, CommandReviewParams),
}


def get_help_text(command_type):
    """
    获取命令支持参数的帮助文档

    Args:
        command_type (CommandType):

    Returns:
        str:
    """
    command, params = COMMAND_MAP[command_type]
    return f"""
### {command_type.value}参数:\n
{params()}
"""
