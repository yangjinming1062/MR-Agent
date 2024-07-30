Fork from https://github.com/Codium-ai/pr-agent
针对gitlab的使用进行定制化修改

# 使用说明

## 部署

1. CI流量已自动构建并推送镜像
2. `docker compose up -d`

## 前提准备

- 在需要添加AI检测的项目中创建一个Project Access Tokens（webhook要用）
- 在项目的Webhooks添加上[部署地址](http://IP:3000/webhook)的监听（部署地址根据实际情况调整 ）
- Secret token处填写上第一步获取到的token（glpat-之后的部分，避免完全一样容易被识别出是token）
- Trigger选择上Comments和Merge Request Events

## 触发条件

开启/重新开启MR的时候会自动添加上使用帮助的comments，按照说明使用即可（具体实现见[help.py](commands%2Fhelp.py)）
