from ._commands_base import *

SYSTEM = """你的任务是标记MR的类型。
{{ DIFF_EXAMPLE }}

{%- if extra_instructions %}
{{ extra_instructions }}
{% endif %}

{{ USE_FORMATTED_OUTPUT }}:
```yaml
{{ LABEL_OF_MR }}:
  {{ LABELS }}
```

输出示例:
```yaml
{{ LABEL_OF_MR }}:
  - 修复BUG
```

{{ YAML_FORMAT }}
"""


class CommandLabels(CommandBase):
    system_template = SYSTEM

    def __init__(self, git_provider, params, **kwargs):
        super(CommandLabels, self).__init__(git_provider, params)

    def subclass_run(self, model, data):
        assert isinstance(data, dict)
        mr_labels = self.get_labels(data) + self.git_provider.get_labels()
        if self.params.publish_labels:
            self.git_provider.publish_labels(mr_labels)
        else:
            comment = convert_to_markdown(data)
            self.git_provider.publish_comment(comment)
