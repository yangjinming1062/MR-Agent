import json
import shlex

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Request
from fastapi import Response

from commands import handle_request
from defines import *

router = APIRouter()

LEGAL_ACTIONS = {x.value for x in list(CommandType)}


@router.post("/webhook")
async def gitlab_webhook(background_tasks: BackgroundTasks, request: Request):
    """
    Webhook监听接口（命令解析入口）

    Args:
        background_tasks (BackgroundTasks): 后台任务
        request (Request): 请求参数

    Returns:

    """
    # Step 1. 获取访问信息：git地址、访问token
    if not (token := request.headers.get("X-Gitlab-Token")):
        # 加载项目的访问密钥，具体怎么配置的见README.md说明
        return Response(status_code=403)
    token = f"glpat-{token}"  # 拼装成完整的token

    if not (git_base := request.headers.get("X-Gitlab-Instance")):
        # 加载项目的访问密钥，具体怎么配置的见README.md说明
        return Response(status_code=401)

    # Step 2. 解析webhook参数判断是否需要执行命令
    data = await request.json()
    if data.get("object_kind") == "merge_request" and data["object_attributes"].get("action") in ["open", "reopen"]:
        # 新建或者重新开启一个MR的时候
        title = data["object_attributes"].get("title")
        url = data["object_attributes"].get("url")
        if "mr:skip" in data["object_attributes"].get("description", ""):
            background_tasks.add_task(handle_request, git_base, token, url, CommandType.Help, None)
        else:
            background_tasks.add_task(handle_request, git_base, token, url, CommandType.Review, None)
        return {"message": f"{CommandType.Help.value}: {title}"}
    elif data.get("object_kind") == "note" and data["event_type"] == "note":
        # 找到mr的url信息
        if "merge_request" in data:
            url = data["merge_request"].get("url")
        elif url := data["object_attributes"].get("url"):
            url = url.split("#")[0]
        else:
            return Response(status_code=400)
        # 提取评论的内容
        if body := data.get("object_attributes", {}).get("note"):
            # Then, apply user specific settings if exists
            body = body.replace("'", "\\'")
            lexer = shlex.shlex(body, posix=True)
            lexer.whitespace_split = True
            command, *args = list(lexer)
            if command in LEGAL_ACTIONS:
                command = CommandType(command)
                background_tasks.add_task(handle_request, git_base, token, url, command, args)
                return Response(json.dumps({"message": f"{command.value}: Accepted"}), status_code=202)
            else:
                return Response(status_code=422)
    else:
        return Response(status_code=404)
