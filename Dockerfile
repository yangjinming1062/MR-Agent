# 构建运行时环境
FROM python:3.11-slim-buster
# 设置时区
ENV TZ=Asia/Shanghai
# 设置语言
ENV LANG=zh_CN.UTF-8
# 设置工作目录
WORKDIR /app
ENV PYTHONPATH=/app
# 安装python库
RUN pip install --upgrade pip
ADD requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.mirrors.ustc.edu.cn/simple -r requirements.txt
# 拷贝项目内容
COPY . .
### 对外暴露端口
EXPOSE 3000
# 启动web服务
CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=3000"]
