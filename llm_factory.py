# ==========================================
# llm_factory.py - 大模型工厂（负责高可用与多级降级）
# ==========================================
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_robust_llm():
    """
    工厂方法：返回一个带有 fallback（降级链）的 LLM 实例。
    优先用 Sudocode，失败则切 DeepSeek。
    """

    # 1. 主模型：Sudocode 代理 (可能会因为 Cloudflare 崩溃或超时)
    primary_llm = ChatOpenAI(
        model="gpt-5.6-sol",  # 确保这是你当前分组支持的模型
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0,
        timeout=300,  # 设置较长超时时间
        max_retries=1,  # 主模型失败1次就立刻降级，不要死磕
        streaming=True,  # 开启流式，防 Cloudflare 524 超时
    )

    # 2. 备用模型 1：Sudocode 的其他模型 (如果主模型挂了，试试备胎)
    # 如果你不想用同一个代理，这层可以删掉
    fallback_llm_1 = ChatOpenAI(
        model="gpt-5.6-luna",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0,
        timeout=300,
        streaming=True,
    )

    # 3. 备用模型 2：DeepSeek 官方 API (完全独立的生命线)
    fallback_llm_2 = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        temperature=0,
        timeout=300,
    )

    # 4. 组装降级链
    # 当 primary_llm 报错时，会自动尝试 fallback_llm_1，再不行尝试 fallback_llm_2
    robust_llm = primary_llm.with_fallbacks(
        [fallback_llm_1, fallback_llm_2],
        exceptions_to_handle=(Exception,),  # 捕获所有网络或 API 异常
    )

    return robust_llm