# ==========================================
# llm_analyzer.py - 大模型智能分析模块 (兼容推理模型版)
# ==========================================
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.output_parsers import PydanticOutputParser

# 引入模型工厂
from llm_factory import get_robust_llm
from models import PaperAnalysis

load_dotenv()


def analyze_paper_structure(task_dir: str) -> dict:
    text_path = Path(task_dir) / "extracted_text.md"
    save_path = Path(task_dir) / "analysis.json"

    if not text_path.exists():
        raise FileNotFoundError(f"找不到提取的文本文件：{text_path}")

    with open(text_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    text_to_analyze = full_text[:30000]

    robust_llm = get_robust_llm()
    parser = PydanticOutputParser(pydantic_object=PaperAnalysis)

    prompt = f"""
    你是一个顶级的 AI 研究员。现在请你阅读以下论文片段，并提取出复现该论文所需的核心信息。

    【重要要求】：
    1. 你必须严格输出合法的 JSON 格式，不要包含任何 Markdown 代码块标记（如 ```json），也不要包含任何额外的解释性文字。
    2. 在 `core_principle` 字段中，如果包含数学公式，请将所有的**行间独立公式**用 `$$` 包裹起来，行内公式用 `$` 包裹。

    {parser.get_format_instructions()}

    论文文本如下：
    {text_to_analyze}
    """

    print(f"正在调用大模型分析论文: {task_dir}")

    try:
        raw_response = robust_llm.invoke(prompt)
        content = raw_response.content

        # ==========================================================
        # 核心修复：处理模型返回复杂列表（包含 reasoning 推理链）的情况
        # ==========================================================
        if isinstance(content, list):
            text_parts = []
            for item in content:
                # 只提取明确带有 text 字段的字典
                if isinstance(item, dict) and "text" in item and item["text"]:
                    text_parts.append(item["text"])

            if text_parts:
                content = "\n".join(text_parts)
            else:
                # 如果列表里全是 reasoning / encrypted_content 这种，直接抛出异常触发降级
                raise ValueError(f"模型返回了非预期的推理结构，未找到纯文本结果。")

        if not isinstance(content, str):
            content = str(content)

        print(f"📝 原始返回预览: {content[:150]}...")

        # 极致清洗：使用正则提取 JSON 块
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            raise ValueError(f"模型返回中未找到 JSON 结构。原始内容: {content[:500]}")

        clean_json_str = json_match.group(0)

        # 尝试解析 JSON
        try:
            result_dict = json.loads(clean_json_str)
        except json.JSONDecodeError as je:
            # 如果标准 json.loads 失败，用 Pydantic 容错解析
            result = parser.parse(clean_json_str)
            result_dict = result.model_dump()

        # 兜底：确保字典中包含所有必填字段
        required_fields = ["core_principle", "target_metrics", "dataset_name", "environment_dependencies"]
        for field in required_fields:
            if field not in result_dict:
                if field == "core_principle":
                    result_dict[field] = "未提取到"
                elif field == "target_metrics":
                    result_dict[field] = {}
                elif field == "dataset_name":
                    result_dict[field] = "Unknown"
                elif field == "environment_dependencies":
                    result_dict[field] = []

        print("✅ 成功解析模型返回的 JSON")

    except Exception as e:
        print(f"❌ 模型分析彻底失败: {e}")
        # 如果主模型因为推理链报错，这里返回兜底数据
        result_dict = {
            "core_principle": f"解析失败，模型可能不支持标准 JSON 输出。错误信息：{str(e)}",
            "target_metrics": {},
            "dataset_name": "Unknown",
            "environment_dependencies": []
        }

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)

    return result_dict