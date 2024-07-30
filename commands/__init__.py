from .describe import CommandDescribe
from .describe import CommandDescribeParams
from .help import COMMAND_MAP
from .help import CommandHelp
from .labels import CommandLabels
from .review import CommandReview
from .review import CommandReviewParams
from core import *
from utils import *


def _parse_args(args):
    """
    解析传递额外的命令参数

    Args:
        args (list[str]): 参数列表

    Returns:
        dict
    """
    args_dict = {}
    for a in args or []:
        if a.startswith("--"):
            tmp = a.split("=", 1)
            k = tmp[0][2:]
            if len(tmp) > 1:
                args_dict[k] = tmp[1]
            else:
                args_dict[k] = True
        elif a.startswith("-"):
            args_dict[a[1:]] = True
    return args_dict


async def handle_request(git_base, token, mr_url, command, args):
    """
    处理Webhook请求，根据不同的命令类型调用具体的实现

    Args:
        git_base (str): https://git.xxx.cn gitlab的地址
        token (str): 项目的访问密钥glpat-xxx
        mr_url (str): merge request的URL
        command (CommandType): 执行的命令
        args (list | None): 附加参数

    Returns:
        None
    """
    # Step 1. 解析命令参数
    args_dict = _parse_args(args)
    # Step 2. 根据不同的命令选择不同的执行类
    command_cls, params_cls = COMMAND_MAP[command]
    # Step 3. 实例化GitProvider以及附加参数
    params = params_cls.deserialize(args_dict)
    git_provider = GitProvider(git_base, token, mr_url)
    item = command_cls(git_provider, params, original_params=args_dict)
    # Step 4. 统一执行命令的调用
    try:
        git_provider.publish_comment("命令执行中，请稍后...", is_temporary=True)
        await item.run()
    except Exception as ex:
        logger.exception(ex)
    finally:
        git_provider.remove_initial_comment()
