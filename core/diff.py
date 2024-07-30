import fnmatch
import re

from .git_provider import GitProvider
from .tokens import TokenHandler
from defines import *
from utils import *

ADDED_FILES_ = "其他新增的文件:\n"
DELETED_FILES_ = "其他删除的文件:\n"
MODIFIED_FILES_ = "其他修改的文件:\n"

TOKENS_SOFT_BUFFER_THRESHOLD = 1000
TOKENS_HARD_BUFFER_THRESHOLD = 600


def get_diff(git, token_handler, add_line_numbers_to_hunks=False, patch_extra_lines=0):
    """
    返回一个包含合并请求diff的字符串，必要时应用diff最小化技术。

    Args:
        git (GitProvider): GitProvider实例
        token_handler (TokenHandler): TokenHandler实例
        add_line_numbers_to_hunks (bool): 是否向diff中的块添加行号。默认为False。
        patch_extra_lines (int): 额外的上下文代码。

    Returns:
        str: 包含合并请求diff的字符串，如果需要，应用diff最小化技术。
    """
    # Step 1.获取差异文件
    try:
        diff_files = git.get_diff_files()
    except Exception as e:
        logger.error(f"Git Error. original message {e=}")
        raise

    # Step 2.过滤忽略的文件
    diff_files = _filter_ignored(diff_files)

    # Step 3.按照主要语言对变更文件排序
    languages = _sort_files_by_main_languages(git.get_languages(), diff_files)

    # Step 3.生成带有补丁扩展名的标准diff字符串
    total_tokens = token_handler.prompt_tokens  # initial tokens
    patches_extended = []
    for lang in languages:
        for file in lang.files:
            if not (patch := file.patch):
                continue
            # extend each patch with extra lines of context
            extended_patch = _extend_patch(file.base_file, patch, num_lines=patch_extra_lines)
            full_extended_patch = f"\n\n## {file.filename}\n\n{extended_patch}\n"
            if add_line_numbers_to_hunks:
                full_extended_patch = _convert_to_hunks_with_lines_numbers(extended_patch, file)
            patch_tokens = token_handler.count_tokens(full_extended_patch)
            file.tokens = patch_tokens
            total_tokens += patch_tokens
            patches_extended.append(full_extended_patch)

    # Step 4.没超阈值则返回全部差异, 否则对差异进行修剪
    if total_tokens + TOKENS_SOFT_BUFFER_THRESHOLD < token_handler.max_tokens:
        return "\n".join(patches_extended)
    else:
        return _clip_diff(languages, token_handler, add_line_numbers_to_hunks)


def _filter_ignored(files):
    """
    过滤掉特定的文件（过滤规则配置在configuration.toml的ignore配置）

    Args:
        files (list[FilePatchInfo])

    Returns:
        list[FilePatchInfo]
    """

    try:
        # load regex patterns, and translate glob patterns to regex
        patterns = CONFIG.ignore.regex
        patterns += [fnmatch.translate(glob) for glob in CONFIG.ignore.glob]

        # compile all valid patterns
        compiled_patterns = []
        for r in patterns:
            try:
                compiled_patterns.append(re.compile(r))
            except re.error:
                pass

        # 保留不匹配忽略正则表达式的文件
        for r in compiled_patterns:
            files = [f for f in files if (f.filename and not r.match(f.filename))]

    except Exception as e:
        logger.error(f"Could not filter file list: {e}")

    return files


def _sort_files_by_main_languages(languages, files):
    """
    按主要语言对文件进行排序，将使用主要语言的文件放在前面，其余文件放在后面

    Args:
        languages (dict):
        files (list[FilePatchInfo]):

    Returns:
        list[LanguageInfo]:
    """
    # 按语言的大小排序
    sorted_languages = [k for k, v in sorted(languages.items(), key=lambda item: item[1], reverse=True)]
    # 获取语言的所有扩展名
    main_extensions = [LANGUAGE_EXTENSION_MAP.get(language.lower(), set()) for language in sorted_languages]
    # 过滤掉不良扩展名的文件
    filtered_files = [f for f in files if f.filename and is_valid_file(f.filename)]

    files_sorted = []
    rest_files = {}

    # 如果没有检测到语言，将所有文件放在“其他”类别中
    if not languages:
        return [({"language": "Other", "files": filtered_files})]

    main_extensions_flat = {x for ext in main_extensions for x in ext}

    for extensions, lang in zip(main_extensions, sorted_languages):  # noqa: B905
        tmp = []
        for file in filtered_files:
            extension_str = f".{file.filename.split('.')[-1]}"
            if extension_str in extensions:
                tmp.append(file)
            else:
                if (file.filename not in rest_files) and (extension_str not in main_extensions_flat):
                    rest_files[file.filename] = file
        if tmp:
            files_sorted.append(LanguageInfo(lang, tmp))
    files_sorted.append(LanguageInfo("Other", list(rest_files.values())))
    return files_sorted


def _convert_to_hunks_with_lines_numbers(patch, file):
    """
        Convert a given patch string into a string with line numbers for each hunk, indicating the new and old content of
        the file.

        Args:
            patch (str): The patch string to be converted.
            file: An object containing the filename of the file being patched.

        Returns:
            str: A string with line numbers for each hunk, indicating the new and old content of the file.

        example output:
    ## src/file.ts
    __new hunk__
    881        line1
    882        line2
    883        line3
    887 +      line4
    888 +      line5
    889        line6
    890        line7
    ...
    __old hunk__
            line1
            line2
    -       line3
    -       line4
            line5
            line6
               ...
    """

    patch_with_lines_str = f"\n\n## {file.filename}\n"
    re_hunk_header = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")
    new_content_lines = []
    old_content_lines = []
    match = None
    start1, size1, start2, size2 = -1, -1, -1, -1
    prev_header_line = []
    header_line = []
    for line in patch.splitlines():
        if "no newline at end of file" in line.lower():
            continue

        if line.startswith("@@"):
            header_line = line
            match = re_hunk_header.match(line)
            if match and new_content_lines:  # found a new hunk, split the previous lines
                if new_content_lines:
                    if prev_header_line:
                        patch_with_lines_str += f"\n{prev_header_line}\n"
                    patch_with_lines_str += "__new hunk__\n"
                    for i, line_new in enumerate(new_content_lines):
                        patch_with_lines_str += f"{start2 + i} {line_new}\n"
                if old_content_lines:
                    patch_with_lines_str += "__old hunk__\n"
                    for line_old in old_content_lines:
                        patch_with_lines_str += f"{line_old}\n"
                new_content_lines = []
                old_content_lines = []
            if match:
                prev_header_line = header_line
        elif line.startswith("+"):
            new_content_lines.append(line)
        elif line.startswith("-"):
            old_content_lines.append(line)
        else:
            new_content_lines.append(line)
            old_content_lines.append(line)

    # finishing last hunk
    if match and new_content_lines:
        if new_content_lines:
            patch_with_lines_str += f"\n{header_line}\n"
            patch_with_lines_str += "\n__new hunk__\n"
            for i, line_new in enumerate(new_content_lines):
                patch_with_lines_str += f"{start2 + i} {line_new}\n"
        if old_content_lines:
            patch_with_lines_str += "\n__old hunk__\n"
            for line_old in old_content_lines:
                patch_with_lines_str += f"{line_old}\n"

    return patch_with_lines_str.rstrip()


def _extend_patch(original_file_str, patch_str, num_lines):
    """
    扩展给定的补丁以包含指定数量的周围行。

    Args:
        original_file_str (str | bytes): 原始文件内容
        patch_str (str): 补丁信息
        num_lines (int): 要包含在扩展补丁中的周围行数。

    Returns:
        str: 扩展的补丁字符串。
    """
    if not patch_str or num_lines == 0:
        return patch_str

    if isinstance(original_file_str, bytes):
        original_file_str = original_file_str.decode("utf-8")

    original_lines = original_file_str.splitlines()
    extended_patch_lines = []

    start1, size1, start2, size2 = -1, -1, -1, -1
    re_hunk_header = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")
    try:
        for line in patch_str.splitlines():
            if line.startswith("@@"):
                if match := re_hunk_header.match(line):
                    # finish previous hunk
                    if start1 != -1:
                        extended_patch_lines.extend(original_lines[start1 + size1 - 1 : start1 + size1 - 1 + num_lines])

                    res = [x or 0 for x in list(match.groups())]

                    try:
                        start1, size1, start2, size2 = map(int, res[:4])
                    except:  # '@@ -0,0 +1 @@' case
                        start1, size1, size2 = map(int, res[:3])
                        start2 = 0
                    section_header = res[4]
                    extended_start1 = max(1, start1 - num_lines)
                    extended_size1 = size1 + (start1 - extended_start1) + num_lines
                    extended_start2 = max(1, start2 - num_lines)
                    extended_size2 = size2 + (start2 - extended_start2) + num_lines
                    extended_patch_lines.append(
                        f"@@ -{extended_start1},{extended_size1} "
                        f"+{extended_start2},{extended_size2} @@ {section_header}"
                    )
                    extended_patch_lines.extend(original_lines[extended_start1 - 1 : start1 - 1])  # one to zero based
                    continue
            extended_patch_lines.append(line)
    except Exception as e:
        logger.debug(f"Failed to extend patch: {e}")
        return patch_str

    # finish previous hunk
    if start1 != -1:
        extended_patch_lines.extend(original_lines[start1 + size1 - 1 : start1 + size1 - 1 + num_lines])

    return "\n".join(extended_patch_lines)


def _clip_diff(languages, token_handler, add_line_numbers_to_hunks):
    """
    修剪差异字符串以满足tokens限制

    Args:
        languages (list[LanguageInfo]):
        token_handler (TokenHandler):
        add_line_numbers_to_hunks (bool):

    Returns:
        str: 修剪后的diff字符串

    Minimization techniques to reduce the number of tokens:
    0. Start from the largest diff patch to smaller ones
    1. Don't use extend context lines around diff
    2. Minimize deleted files
    3. Minimize deleted hunks
    4. Minimize all remaining files when you reach token limit
    """

    patches = []
    added_files_list = []
    modified_files_list = []
    deleted_files_list = []
    # sort each one of the languages in top_langs by the number of tokens in the diff
    sorted_files = []
    for lang in languages:
        sorted_files.extend(sorted(lang.files, key=lambda x: x.tokens, reverse=True))

    total_tokens = token_handler.prompt_tokens
    for file in sorted_files:
        if not file.patch:
            continue

        patch = _handle_patch_deletions(file)
        if patch is None:
            # 整个文件都是删除的就只记录名字
            if not deleted_files_list:
                total_tokens += token_handler.count_tokens(DELETED_FILES_)
            deleted_files_list.append(file.filename)
            total_tokens += token_handler.count_tokens(file.filename) + 1
            continue

        if add_line_numbers_to_hunks:
            patch = _convert_to_hunks_with_lines_numbers(patch, file)

        # tokens不足，硬终止
        if total_tokens > token_handler.max_tokens - TOKENS_HARD_BUFFER_THRESHOLD:
            logger.warning(f"tokens不足，文件被忽略: {file.filename}")
            continue

        # 如果补丁太大，只显示文件名
        if total_tokens + token_handler.count_tokens(patch) > token_handler.max_tokens - TOKENS_SOFT_BUFFER_THRESHOLD:
            # Current logic is to skip the patch if it's too large
            logger.debug(f"Patch too large, minimizing it, {file.filename}")
            if file.edit_type == EditType.ADDED:
                if not added_files_list:
                    total_tokens += token_handler.count_tokens(ADDED_FILES_)
                added_files_list.append(file.filename)
            else:
                if not modified_files_list:
                    total_tokens += token_handler.count_tokens(MODIFIED_FILES_)
                modified_files_list.append(file.filename)
                total_tokens += token_handler.count_tokens(file.filename) + 1
            continue

        if patch:
            if not add_line_numbers_to_hunks:
                patch_final = f"## {file.filename}\n\n{patch}\n"
            else:
                patch_final = patch
            patches.append(patch_final)
            total_tokens += token_handler.count_tokens(patch_final)
            logger.debug(f"Tokens: {total_tokens}, last filename: {file.filename}")

    final_diff = "\n".join(patches)
    if added_files_list:
        added_list_str = ADDED_FILES_ + "\n".join(added_files_list)
        final_diff = final_diff + "\n\n" + added_list_str
    if modified_files_list:
        modified_list_str = MODIFIED_FILES_ + "\n".join(modified_files_list)
        final_diff = final_diff + "\n\n" + modified_list_str
    if deleted_files_list:
        deleted_list_str = DELETED_FILES_ + "\n".join(deleted_files_list)
        final_diff = final_diff + "\n\n" + deleted_list_str
    return final_diff


def _handle_patch_deletions(file):
    """
    返回移除了删除块的补丁字符串

    Args:
        file (FilePatchInfo): 文件实例

    Returns:
        str: 忽略掉删除块后的补丁字符串。
    """

    def _omit_deletion_hunks(patch_lines):
        """
        Omit deletion hunks from the patch and return the modified patch.

        Args:
            patch_lines (list): a list of strings representing the lines of the patch

        Returns:
            str: A string representing the modified patch with deletion hunks omitted
        """

        temp_hunk = []
        added_patched = []
        add_hunk = False
        inside_hunk = False
        re_hunk_header = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))?\ @@[ ]?(.*)")

        for line in patch_lines:
            if line.startswith("@@"):
                if re_hunk_header.match(line):
                    # finish previous hunk
                    if inside_hunk and add_hunk:
                        added_patched.extend(temp_hunk)
                        temp_hunk = []
                        add_hunk = False
                    temp_hunk.append(line)
                    inside_hunk = True
            else:
                temp_hunk.append(line)
                if line[0] == "+":
                    add_hunk = True
        if inside_hunk and add_hunk:
            added_patched.extend(temp_hunk)

        return "\n".join(added_patched)

    if not file.head_file and file.edit_type == EditType.DELETED:
        # logic for handling deleted files - don't show patch, just show that the file was deleted
        logger.info(f"Processing file: {file.filename}, minimizing deletion file")
        return None
    else:
        patch_new = _omit_deletion_hunks(file.patch.splitlines())
        if file.patch != patch_new:
            logger.info(f"Processing file: {file.filename}, hunks were deleted")
        return patch_new
