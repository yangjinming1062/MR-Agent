import uvicorn
from fastapi import FastAPI

from api import router


def create_app():
    """
    创建并配置FastAPI的APP。

    Returns:
        FastAPI: 添加上路由信息的APP。
    """
    _app = FastAPI(title="MR-Agent", description="", version="main")
    _app.include_router(router)

    return _app


app = create_app()
if __name__ == "__main__":  # Debug时使用该方法
    uvicorn.run(app, host="0.0.0.0", port=3000)
