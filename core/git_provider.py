import difflib
import re
from typing import Any
from urllib.parse import urlparse

import gitlab
from gitlab import GitlabGetError

from defines import *
from utils import *


def _load_large_diff(filename, new_file_content, original_file_content):
    """
    Generate a patch for a modified file by comparing the original content of the file with the new content provided as
    input.

    Args:
        new_file_content (str): The new content of the file as a string.
        original_file_content (str): The original content of the file as a string.

    Returns:
        str: The generated or provided patch string.

    Raises:
        None.
    """
    patch = ""
    try:
        diff = difflib.unified_diff(
            original_file_content.splitlines(keepends=True), new_file_content.splitlines(keepends=True)
        )
        logger.debug(f"File was modified, but no patch was found. Manually creating patch: {filename}.")
        patch = "".join(diff)
    except Exception:
        pass
    return patch


def _find_line_number_of_relevant_line_in_file(diff_files, relevant_file, relevant_line_in_file):
    """
    Find the line number and absolute position of a relevant line in a file.

    Args:
        diff_files (list[FilePatchInfo]): A list of FilePatchInfo objects representing the patches of files.
        relevant_file (str): The name of the file where the relevant line is located.
        relevant_line_in_file (str): The content of the relevant line.

    Returns:
        tuple[int, int]: A tuple containing the line number and absolute position of the relevant line in the file.
    """
    position = -1
    absolute_position = -1
    re_hunk_header = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[ ]?(.*)")

    for file in diff_files:
        if file.filename and (file.filename.strip() == relevant_file):
            patch = file.patch
            patch_lines = patch.splitlines()

            # try to find the line in the patch using difflib, with some margin of error
            matches_difflib: list[str | Any] = difflib.get_close_matches(
                relevant_line_in_file, patch_lines, n=3, cutoff=0.93
            )
            if len(matches_difflib) == 1 and matches_difflib[0].startswith("+"):
                relevant_line_in_file = matches_difflib[0]

            delta = 0
            start1, size1, start2, size2 = 0, 0, 0, 0
            for i, line in enumerate(patch_lines):
                if line.startswith("@@"):
                    delta = 0
                    match = re_hunk_header.match(line)
                    start1, size1, start2, size2 = map(int, match.groups()[:4])
                elif not line.startswith("-"):
                    delta += 1

                if relevant_line_in_file in line and line[0] != "-":
                    position = i
                    absolute_position = start2 + delta - 1
                    break

            if position == -1 and relevant_line_in_file[0] == "+":
                no_plus_line = relevant_line_in_file[1:].lstrip()
                for i, line in enumerate(patch_lines):
                    if line.startswith("@@"):
                        delta = 0
                        match = re_hunk_header.match(line)
                        start1, size1, start2, size2 = map(int, match.groups()[:4])
                    elif not line.startswith("-"):
                        delta += 1

                    if no_plus_line in line and line[0] != "-":
                        # The model might add a '+' to the beginning of the relevant_line_in_file even if originally
                        # it's a context line
                        position = i
                        absolute_position = start2 + delta - 1
                        break
    return position, absolute_position


def get_main_language(languages, files):
    """
    Get the main language of the commit. Return an empty string if cannot determine.

    Args:
        languages:
        files:

    Returns:
        str: The main language of the commit.
    """
    main_language = ""
    if not languages:
        logger.info("No languages detected")
        return main_language
    if not files:
        logger.info("No files in diff")
        return main_language

    try:
        top_language = max(languages, key=languages.get).lower()

        # validate that the specific commit uses the main language
        extension_list = []
        for file in files:
            if not file:
                continue
            if isinstance(file, str):
                file = FilePatchInfo(base_file=None, head_file=None, patch=None, filename=file)
            extension_list.append(file.filename.rsplit(".")[-1])

        # get the most common extension
        most_common_extension = max(set(extension_list), key=extension_list.count)

        # look for a match. TBD: add more languages, do this systematically
        if (
            most_common_extension == "py"
            and top_language == "python"
            or most_common_extension == "js"
            and top_language == "javascript"
            or most_common_extension == "ts"
            and top_language == "typescript"
            or most_common_extension == "go"
            and top_language == "go"
            or most_common_extension == "java"
            and top_language == "java"
            or most_common_extension == "c"
            and top_language == "c"
            or most_common_extension == "cpp"
            and top_language == "c++"
            or most_common_extension == "cs"
            and top_language == "c#"
            or most_common_extension == "swift"
            and top_language == "swift"
            or most_common_extension == "php"
            and top_language == "php"
            or most_common_extension == "rb"
            and top_language == "ruby"
            or most_common_extension == "rs"
            and top_language == "rust"
            or most_common_extension == "scala"
            and top_language == "scala"
            or most_common_extension == "kt"
            and top_language == "kotlin"
            or most_common_extension == "pl"
            and top_language == "perl"
            or most_common_extension == top_language
        ):
            main_language = top_language

    except Exception as e:
        logger.exception(e)

    return main_language


class GitProvider:

    def __init__(self, git_base, token, mr_url=None):
        self.git = gitlab.Gitlab(url=git_base, oauth_token=token)
        self.project_id = None
        self.mr_id = mr_url
        self.mr = None
        self.diff_files = None
        self.git_files = None
        self.temp_comments = []
        self._set_merge_request(mr_url)

    def _set_merge_request(self, mr_url):
        """
        根据mr的url查询出对应的mr信息

        Args:
            mr_url (str):

        Returns:

        """
        self.project_id, mr_id = self._parse_merge_request_url(mr_url)
        self.mr = self.git.projects.get(self.project_id).mergerequests.get(mr_id)
        try:
            self.last_diff = self.mr.diffs.list(get_all=True)[-1]
        except IndexError as e:
            raise Exception(f"Could not get diff for {self.mr_id}") from e

    def get_description(self, token_handler, *, full=True):
        """
        获取合并请求的描述

        Args:
            token_handler (TokenHandler):
            full (bool): Defaults to True

        Returns:
            str: merge request description
        """
        description = self.mr.description if full else self.get_user_description()
        return clip_tokens(token_handler, description, MAX_DESCRIPTION_TOKENS)

    def get_user_description(self):
        """
        Get user description

        Returns:
            str
        """
        description = (self.mr.description or "").strip()
        if not any(
            description.startswith(header) for header in {f"## {CONSTANTS.LABEL_OF_MR}", f"## {CONSTANTS.DESCRIPTION}"}
        ):
            return description
        # if the existing description was generated by the mr-agent, but it doesn't contain the user description,
        # return nothing (empty string) because it means there is no user description
        if f"## {CONSTANTS.USER_DESCRIPTION}" not in description:
            return ""
        # otherwise, extract the original user description from the existing mr-agent description and return it
        return description.split(f"## {CONSTANTS.USER_DESCRIPTION}:", 1)[1].strip()

    def _get_file_content(self, file_path, branch):
        """
        Get file content from GitLab

        Args:
            file_path (str):
            branch (str):

        Returns:
            str: file content
        """
        try:
            return self.git.projects.get(self.project_id).files.get(file_path, branch).decode()
        except GitlabGetError:
            # In case of file creation the method returns GitlabGetError (404 file not found).
            # In this case we return an empty string for the diff.
            return ""

    def get_diff_files(self):
        """
        检索在MR中被修改、添加、删除或重命名的文件列表，以及它们的内容和补丁信息。

        Returns:
            list[FilePatchInfo]: MR中修改、添加、删除或重命名的文件列表。
        """

        if self.diff_files:
            return self.diff_files

        self.diff_files = []
        for diff in self.mr.changes()["changes"]:
            if is_valid_file(diff["new_path"]):
                # original_file_content = self._get_pr_file_content(diff['old_path'], self.mr.target_branch)
                # new_file_content = self._get_pr_file_content(diff['new_path'], self.mr.source_branch)
                original_file_content = self._get_file_content(diff["old_path"], self.mr.diff_refs["base_sha"])
                new_file_content = self._get_file_content(diff["new_path"], self.mr.diff_refs["head_sha"])

                try:
                    if isinstance(original_file_content, bytes):
                        original_file_content = bytes.decode(original_file_content, "utf-8")
                    if isinstance(new_file_content, bytes):
                        new_file_content = bytes.decode(new_file_content, "utf-8")
                except UnicodeDecodeError:
                    logger.warning(f"{self.mr_id=}: 文件解码失败 {diff['old_path']} or {diff['new_path']}")

                if diff["new_file"]:
                    edit_type = EditType.ADDED
                elif diff["deleted_file"]:
                    edit_type = EditType.DELETED
                elif diff["renamed_file"]:
                    edit_type = EditType.RENAMED
                else:
                    edit_type = EditType.MODIFIED

                filename = diff["new_path"]

                self.diff_files.append(
                    FilePatchInfo(
                        original_file_content,
                        new_file_content,
                        patch=diff["diff"] or _load_large_diff(filename, new_file_content, original_file_content),
                        filename=filename,
                        edit_type=edit_type,
                        old_filename=None if diff["old_path"] == diff["new_path"] else diff["old_path"],
                    )
                )
        return self.diff_files

    def get_files(self):
        if not self.git_files:
            self.git_files = [change["new_path"] for change in self.mr.changes()["changes"]]
        return self.git_files

    def publish_description(self, title, body):
        """
        Updates the description of the merge request in GitLab

        Args:
            title (str):
            body (str):

        Returns:
            None
        """
        try:
            self.mr.title = title
            self.mr.description = body
            self.mr.save()
        except Exception as e:
            logger.exception(f"Could not update merge request {self.mr_id} description: {e}")

    def get_latest_commit_url(self):
        return self.mr.commits().next().web_url

    def get_comment_url(self, comment):
        return f"{self.mr.web_url}#note_{comment.id}"

    def publish_persistent_comment(self, mr_comment: str, initial_header: str, update_header: bool = True):
        try:
            for comment in self.mr.notes.list(get_all=True)[::-1]:
                if comment.body.startswith(initial_header):
                    latest_commit_url = self.get_latest_commit_url()
                    comment_url = self.get_comment_url(comment)
                    if update_header:
                        updated_header = f"{initial_header}\n\n### (提交 {latest_commit_url} 之后已更新)\n"
                        updated_comment = mr_comment.replace(initial_header, updated_header)
                    else:
                        updated_comment = mr_comment
                    self.mr.notes.update(comment.id, {"body": updated_comment})
                    self.publish_comment(f"**[评论]({comment_url})** 已更新")
                    return
        except Exception as e:
            logger.exception(f"Failed to update persistent review: {e=}")
        self.publish_comment(mr_comment)

    def publish_comment(self, mr_comment: str, is_temporary: bool = False):
        comment = self.mr.notes.create({"body": mr_comment})
        # self.mr.discussions.get('0851d5df3306adec64eade2940777d881e2a49eb').notes.create(
        #     {'body': 'replay test'})
        if is_temporary:
            self.temp_comments.append(comment)

    def remove_initial_comment(self):
        for comment in self.temp_comments:
            self.remove_comment(comment)

    def remove_comment(self, comment):
        try:
            comment.delete()
        except Exception as e:
            logger.exception(f"Failed to remove comment, error: {e}")

    def get_languages(self):
        languages = self.git.projects.get(self.project_id).languages()
        return languages

    def get_mr_branch(self):
        return self.mr.source_branch

    def _parse_merge_request_url(self, merge_request_url):
        """

        Args:
            merge_request_url (str):

        Returns:
            tuple[str, int]
        """
        parsed_url = urlparse(merge_request_url)

        path_parts = parsed_url.path.strip("/").split("/")
        if "merge_requests" not in path_parts:
            raise ValueError("The provided URL does not appear to be a GitLab merge request URL")

        mr_index = path_parts.index("merge_requests")
        # Ensure there is an ID after 'merge_requests'
        if len(path_parts) <= mr_index + 1:
            raise ValueError("The provided URL does not contain a merge request ID")

        try:
            mr_id = int(path_parts[mr_index + 1])
        except ValueError as e:
            raise ValueError("Unable to convert merge request ID to integer") from e

        # Handle special delimiter (-)
        project_path = "/".join(path_parts[:mr_index])
        if project_path.endswith("/-"):
            project_path = project_path[:-2]

        # Return the path before 'merge_requests' and the ID
        return project_path, mr_id

    def publish_labels(self, mr_types):
        try:
            self.mr.labels = list(set(mr_types))
            self.mr.save()
        except Exception as e:
            logger.exception(f"Failed to publish labels: {e=}")

    def get_labels(self):
        """
        获取MR当前的标签。

        Returns:
            list:
        """
        return self.mr.labels

    def get_commit_messages(self, token_handler):
        """
        Retrieves the commit messages of a merge request.

        Args
            token_handler (TokenHandler):

        Returns:
            str: A string containing the commit messages of the merge request.
        """
        try:
            commit_messages_list = [commit["message"] for commit in self.mr.commits()._list]
            commit_messages_str = "\n".join([f"{i + 1}. {message}" for i, message in enumerate(commit_messages_list)])
        except Exception:
            commit_messages_str = ""
        return clip_tokens(token_handler, commit_messages_str, MAX_COMMITS_TOKENS)

    def generate_link_to_relevant_line_number(self, suggestion):
        """
        生成代码建议中到相关行号的链接

        Args:
            suggestion (dict):

        Returns:
            str
        """
        try:
            relevant_file = suggestion[CONSTANTS.RELEVANT_FILE].strip("`").strip("'")
            relevant_line_str = suggestion[CONSTANTS.EXISTING_CODE]
            if not relevant_line_str:
                return ""
            relevant_line_str = relevant_line_str.split("\n")[0]

            position, absolute_position = _find_line_number_of_relevant_line_in_file(
                self.diff_files, relevant_file, relevant_line_str
            )

            if absolute_position != -1:
                # link to right file only
                project_url = self.mr.web_url.rsplit("-", 1)[0]
                url = f"{project_url}-/blob/{self.mr.source_branch}/{relevant_file}?ref_type=heads#L{absolute_position}"
                return relevant_line_str, url
        except Exception as e:
            logger.debug(f"Failed adding line link {e=}")
