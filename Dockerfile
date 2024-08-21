# 使用官方 Python 运行时作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 将当前目录的内容复制到工作目录中
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir aiohttp pyquery selenium chardet flask requests

# 设置环境变量，以防止 Python 缓存生成
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 暴露 Flask 服务器的端口
EXPOSE 5000

# 运行主 Python 脚本
CMD ["python", "main.py"]
