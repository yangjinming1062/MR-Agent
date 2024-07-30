from collections import OrderedDict

from ._commands_base import *

SYSTEM = """你的任务是为MR提供建设性和简洁的反馈，并提供有意义的代码建议。
{{ DIFF_EXAMPLE }}

{%- if num_code_suggestions > 0 %}
- 如果没有比较重要的可以不提供建议。如果有，最多提供{{ num_code_suggestions }}个代码建议。试着提供多样化和有见地的建议。
- 把重点放在重要的建议上，比如修复代码问题、问题和bug。作为第二个优先事项，为有意义的代码改进提供建议，比如性能、漏洞、模块化和最佳实践。
- 避免提出已经在MR代码中实现过的建议。例如，如果你想添加日志，或将变量更改为const，或其他任何东西，请确保它不在MR代码中。
- 不用建议添加文档字符串、类型提示或注释。
- 不用建议{{ IMPROVED_CODE }}与{{ EXISTING_CODE }}一样的代码。
- 建议应侧重于改进MR中新添加的代码(以“+”开头的行)。
{%- endif %}

{%- if extra_instructions %}
{{ extra_instructions }}
{% endif %}

{{ USE_FORMATTED_OUTPUT }}:
```yaml
{{ ANALYSIS }}:
  {{ THEME }}:
    type: string
    description: 对MR的简短解释
  {{ SUMMARY }}:
    type: string
    description: 用2-3句话总结MR。
{%- if require_score %}
  {{ SCORE }}:
    type: string
    description: |-
      用0-10(包括0和10在内)对MR进行评分，0表示最糟糕的MR代码，10表示质量最高的MR代码，没有任何bug或性能问题。如果你给出的评分不是10分请给出扣分的原因。使用格式:'9,因为…'
{%- endif %}
{%- if require_tests %}
  {{ TESTS }}:
    type: string
    description: 是\\否 问题:这个MR有相关的测试代码吗?
{%- endif %}
{%- if require_error %}
  {{ ERROR }}:
    type: string
    description: 是\\否 问题:这个MR中是否存在代码的语法错误？
{%- endif %}
{%- if require_focused %}
  {{ FOCUSED }}:
    type: string
    description: |-
      从某种意义上说，所有MR代码的变化都统一在一个单一的主题下，这是一个专注的MR吗?如果主题太宽泛，或者MR代码变化太分散，那么MR就没有重点。简短地解释你的答案。
{%- endif %}
{%- if require_estimate %}
  {{ REVIEW_ESTIMATED }}:
    type: string
    description: >-
      从1-5分(包括1-5分)来评估经验丰富、知识渊博的开发人员审查该MR所需的时间和精力。1表示简短而简单的复习，5表示冗长而困难的复习。考虑到MR代码的大小、复杂性、质量和所需的更改。简短地解释你的答案(1-2句话)。使用格式:'1,因为…'
{%- endif %}
{%- if require_security %}
  {{ SECURITY_CONCERNS }}:
    type: string
    description: >-
      此MR代码是否引入了可能的漏洞，例如敏感信息(例如，API密钥、秘密、密码)的暴露，或者SQL注入、XSS、CSRF等安全问题?如果没有可能的问题，请回答“否”。回答“是，因为……”，如果有安全方面的担忧或问题。简短地解释你的答案。
{%- endif %}
{{ LABEL_OF_MR }}:
  {{ LABELS }}
{{ MR_FEEDBACK }}:
  {{ GENERAL_SUGGESTIONS }}:
    type: string
    description: |-
      对MR的贡献者和维护者的一般性建议和反馈。可能包括对MR的总体结构、主要目的、最佳实践、关键bug和其他方面的重要建议。不要讨论MR的标题和描述，或者缺乏测试。解释你的建议。
{%- if num_code_suggestions > 0 %}
  {{ CODE_SUGGESTIONS }}:
    type: array
    maxItems: {{ num_code_suggestions }}
    uniqueItems: true
    items:
    {{ RELEVANT_FILE }}:
      type: string
      description: 相关文件的完整路径
    {{ SUGGESTION }}:
      type: string
      description: |-
        为了改进MR代码而提出的具体的建议
    {{ EXISTING_CODE }}:
      type: string
      description: |-
        一个代码片段，显示了来自'__new hunk__'节的相关代码行。它必须是连续的，格式正确且缩进的，并且没有行号。
    {{ RELEVANT_LINE_START }}:
      type: integer
      description: |-
        建议开始的'__new hunk__'部分的相关行号(包括)。应该是从大块行号派生出来的，并对应于上面的“{{ EXISTING_CODE }}”片段。
    {{ RELEVANT_LINE_END }}:
      type: integer
      description: |-
        建议结束的'__new hunk__'部分的相关行号(包括)。应该是从大块行号派生出来的，并对应于上面的“{{ EXISTING_CODE }}”片段。
    {{ IMPROVED_CODE }}:
      type: string
      description: |-
        一个新的代码片段，可用于替换'__new hunk__'代码中的相关行。替换建议应该是完整的，格式正确，缩进，没有行号。
{%- endif %}
```

输出示例:
```yaml
{{ ANALYSIS }}:
  {{ THEME }}: |-
    xxx
  {{ SUMMARY }}: |-
    xxx
{%- if require_score %}
  {{ SCORE }}: |-
    9, 因为 ...
{%- endif %}
{%- if require_tests %}
  {{ TESTS }}: |-
    是
{%- endif %}
{%- if require_error %}
  {{ ERROR }}:
    否
{%- endif %}
{%- if require_focused %}
  {{ FOCUSED }}: 否, 因为 ...
{%- endif %}
{%- if require_estimate %}
  {{ REVIEW_ESTIMATED }}: |-
    3, 因为 ...
{%- endif %}
{%- if require_security %}
  {{ SECURITY_CONCERNS }}: 否
{%- endif %}
{{ LABEL_OF_MR }}:
  - 新功能
{{ MR_FEEDBACK }}:
  {{ GENERAL_SUGGESTIONS }}: |-
    ...
{%- if num_code_suggestions > 0 %}
  {{ CODE_SUGGESTIONS }}:
    - {{ RELEVANT_FILE }}: directory/xxx.py
      {{ SUGGESTION }}: |-
        ...
      {{ EXISTING_CODE }}: |-
        ...
      {{ RELEVANT_LINE_START }}: 1
      {{ RELEVANT_LINE_END }}: 10
      {{ IMPROVED_CODE }}: |-
        ...
    ...
{%- endif %}
```

{{ YAML_FORMAT }}
"""


class CommandReviewParams(CommandParams):
    require_score: bool = Field(True, description="对MR进行评分")
    require_tests: bool = Field(False, description="检查MR中是否包含相关的测试代码")
    require_error: bool = Field(True, description="检查MR中是否包含语法错误的代码")
    require_security: bool = Field(True, description="检查MR中是否包含安全问题")
    require_focused: bool = Field(True, description="检查MR是否聚焦单一主题")
    require_estimate: bool = Field(False, description="评估MR所需的时间和精力")
    num_code_suggestions: int = Field(10, description="代码建议的数量")
    update_description: str = Field("", description="使用哪个模型的分析结论更新描述，默认空字符串表示不更新")
    enable_review_labels_security: bool = Field(True, description="发现安全问题是否需要打个标签")
    enable_review_labels_estimate: bool = Field(False, description="评估MR耗费的时间是否需要打个标签")
    persistent_comment: bool = Field(True, description="持续更新同一个评论")


class CommandReview(CommandBase):
    params: CommandReviewParams
    system_template = SYSTEM

    def __init__(self, git_provider, params, **kwargs):
        super(CommandReview, self).__init__(git_provider, params)

    def subclass_run(self, model, data):
        comment = self._prepare_review(model, data)
        if self.params.persistent_comment:
            self.git_provider.publish_persistent_comment(
                comment, initial_header=f"## {CONSTANTS.ANALYSIS}({model})", update_header=True
            )
        else:
            self.git_provider.publish_comment(comment)

    def _prepare_review(self, model, data):
        # 给最上面的title后附加使用的model
        analysis_key = f"{CONSTANTS.ANALYSIS}({model})"
        result = OrderedDict({analysis_key: data[CONSTANTS.ANALYSIS]})
        mr_feedback = data.get(CONSTANTS.MR_FEEDBACK, {})

        if security_concerns := mr_feedback.pop(CONSTANTS.SECURITY_CONCERNS, None):
            result.setdefault(analysis_key, {})[CONSTANTS.SECURITY_CONCERNS] = security_concerns

        if CONSTANTS.CODE_SUGGESTIONS in mr_feedback:
            mr_feedback[CONSTANTS.CODE_SUGGESTIONS] = self._get_suggestions(mr_feedback[CONSTANTS.CODE_SUGGESTIONS])

        result[CONSTANTS.MR_FEEDBACK] = mr_feedback

        if self.params.update_description == model:
            title = result[analysis_key][CONSTANTS.THEME]
            body = f"{result[analysis_key][CONSTANTS.SUMMARY]}\n\n - generated by {model}"
            self.git_provider.publish_description(title, body)

        labels = self._prepare_labels(self.get_labels(data), result[analysis_key])
        if self.params.publish_labels:
            self.git_provider.publish_labels(labels)
        else:
            result[analysis_key][CONSTANTS.LABEL_OF_MR] = labels

        return convert_to_markdown(result)

    def _get_suggestions(self, data):
        result = []
        for d in data or []:
            if content := d.get(CONSTANTS.SUGGESTION):
                if refer := self.git_provider.generate_link_to_relevant_line_number(d):
                    name, url = refer
                    link = f"[{name}]({url})"
                else:
                    link = f"{d[CONSTANTS.RELEVANT_LINE_START]}~{d[CONSTANTS.RELEVANT_LINE_END]}"
                result.append(
                    {
                        CONSTANTS.SUGGESTION: content,
                        CONSTANTS.RELEVANT_FILE: d[CONSTANTS.RELEVANT_FILE].strip(),
                        CONSTANTS.RELEVANT_LINE: link,
                        CONSTANTS.EXISTING_CODE: d[CONSTANTS.EXISTING_CODE],
                        CONSTANTS.IMPROVED_CODE: d[CONSTANTS.IMPROVED_CODE],
                    }
                )
        return result

    def _prepare_labels(self, review_labels, data):
        """
        为MR添加标签

        Args:
            review_labels (list):
            data (dict):

        Returns:
            list:
        """
        if self.params.enable_review_labels_estimate and CONSTANTS.REVIEW_ESTIMATED in data or {}:
            estimated_effort = data[CONSTANTS.REVIEW_ESTIMATED]
            estimated_effort_number = int(estimated_effort.split(",")[0])
            if 1 <= estimated_effort_number <= 5:  # 1, 因为 ...
                review_labels.append(f"{CONSTANTS.REVIEW_ESTIMATED}: {estimated_effort_number}")
        if self.params.enable_review_labels_security and CONSTANTS.SECURITY_CONCERNS in data or {}:
            if data[CONSTANTS.SECURITY_CONCERNS].startswith("是"):
                review_labels.append(CONSTANTS.SECURITY_CONCERNS)

        current_labels = [
            label
            for label in self.git_provider.get_labels()
            if not label.startswith(CONSTANTS.REVIEW_ESTIMATED) and not label.startswith(CONSTANTS.SECURITY_CONCERNS)
        ]
        return review_labels + current_labels
