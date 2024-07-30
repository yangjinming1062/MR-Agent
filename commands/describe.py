from ._commands_base import *

SYSTEM = """你的任务是根据提交的代码差异提供MR内容的完整描述。
{{ DIFF_EXAMPLE }}
- 请注意，“{{ COMMIT_TITLE }}”、“{{ COMMIT_DESCRIPTION }}”和“{{ COMMIT_MESSAGE }}”部分可能是部分的、简单的、没有信息的或不是最新的。因此，将它们与差异部分的代码进行比较，并仅将它们用作参考。
- 首先强调最重要的更新，然后是次要的更新。

{%- if extra_instructions %}
{{ extra_instructions }}
{% endif %}

{{ USE_FORMATTED_OUTPUT }}:
```yaml
{{ TITLE }}:
  type: string
  description: 一个信息丰富的MR标题，描述它的主题
{{ LABEL_OF_MR }}:
  {{ LABELS }}
{{ DESCRIPTION }}:
  type: string
  description: 对MR翔实而简明的描述。
{{ MAIN_FILES_WALKTHROUGH }}:
  type: array
  maxItems: {{ num_walkthrough }}
  description: |-
    MR主要修改的文件，简要描述每个文件中的更改。
  items:
    {{ FILENAME }}:
      type: string
      description: 相关文件的完整路径
    {{ CHANGES_IN_FILE }}:
      type: string
      description: 在相关文件中对变更进行最小化和简明的描述
```

输出示例:
```yaml
{{ TITLE }}: |-
  ...
{{ LABEL_OF_MR }}:
  - 修复BUG
{{ DESCRIPTION }}: |-
  ...
{{ MAIN_FILES_WALKTHROUGH }}:
  - ...
  - ...
```

{{ YAML_FORMAT }}
"""


class CommandDescribeParams(CommandParams):
    publish_description_as_comment: bool = Field(False, description="将描述作为评论提交")
    add_original_description: bool = Field(False, description="添加原始用户描述")
    keep_original_title: bool = Field(False, description="维持原始标题")
    num_walkthrough: int = Field(10, description="主要变更文件概览的数量")


class CommandDescribe(CommandBase):
    params: CommandDescribeParams
    system_template = SYSTEM

    def __init__(self, git_provider, params, **kwargs):
        super(CommandDescribe, self).__init__(git_provider, params)
        self.user_description = self.git_provider.get_user_description()

    def subclass_run(self, model, data):
        assert isinstance(data, dict)
        if self.params.add_original_description and self.user_description:
            data[CONSTANTS.USER_DESCRIPTION] = self.user_description

        if self.params.publish_labels:
            mr_labels = self.get_labels(data) + self.git_provider.get_labels()
            data.pop(CONSTANTS.LABEL_OF_MR, None)
            self.git_provider.publish_labels(mr_labels)

        title, body = self._prepare_answer(data)

        if self.params.publish_description_as_comment:
            self.git_provider.publish_comment(f"## {CONSTANTS.TITLE}({model})\n\n{title}\n\n___\n{body}")
        else:
            self.git_provider.publish_description(title, body)

    def _prepare_answer(self, data):
        """
        根据AI预测数据准备MR描述。

        Returns:
            tuple[str, str]: title, body
        """

        # 遍历字典项，并以markdown格式将键和值附加到'markdown_text'
        markdown_text = ""

        for key, value in data.items():
            markdown_text += f"## {key}\n\n"
            markdown_text += f"{value}\n\n"

        ai_title = data.pop(CONSTANTS.TITLE, self.variables["title"])
        # 根据keep_original_user_title参数来决定是使用提交的原始标题还是AI预测的标题
        title = self.variables["title"] if self.params.keep_original_title else ai_title

        # 迭代剩余的字典项，并以markdown格式将键和值附加到body，
        # except for the items containing the word 'walkthrough'
        body = ""
        for idx, (key, value) in enumerate(data.items()):
            body += f"## {key}:\n"
            if CONSTANTS.MAIN_FILES_WALKTHROUGH in key:
                # for filename, description in value.items():
                for file in value:
                    filename = file[CONSTANTS.FILENAME].replace("'", "`")
                    description = file[CONSTANTS.CHANGES_IN_FILE]
                    body += f"- `{filename}`: {description}\n"
            else:
                # if the value is a list, join its items by comma
                if isinstance(value, list):
                    value = ", ".join(v for v in value)
                body += f"{value}\n"
            if idx < len(data) - 1:
                body += "\n___\n"

        return title, body
