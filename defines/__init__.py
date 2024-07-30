from .classes import *
from .enums import *
from config import CONFIG

# Language Selection, source: https://github.com/bigcode-project/bigcode-dataset/blob/main/language_selection/programming-languages-to-file-extensions.json  # noqa E501

LANGUAGE_EXTENSION_MAP = {k.lower(): set(v) for k, v in CONFIG.language_extension_map_org.items()}

# Bad Extensions, source: https://github.com/EleutherAI/github-downloader/blob/345e7c4cbb9e0dc8a0615fd995a08bf9d73b3fe6/download_repo_text.py  # noqa: E501
BAD_EXTENSIONS = set(CONFIG.bad_extensions.default + CONFIG.bad_extensions.extra)
MAX_DESCRIPTION_TOKENS = 500
MAX_COMMITS_TOKENS = 500

USER_TEMPLATE = """MR信息:
{{ COMMIT_TITLE }}: '{{title}}'
{{ COMMIT_BRANCH }}: '{{branch}}'
{{ COMMIT_DESCRIPTION }}: '{{description}}'

{%- if language %}
主要语言: {{language}}
{%- endif %}

{%- if commit_messages_str %}
{{ COMMIT_MESSAGE }}:
{{commit_messages_str}}
{%- endif %}

差异部分:
```
{{diff}}
```
请注意，差异部分中的行以表示更改类型的符号为前缀:“-”表示删除，“+”表示添加。专注于“+”的行。
"""
