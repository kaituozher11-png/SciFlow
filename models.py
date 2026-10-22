# ==========================================
# models.py - 定义所有 Agent 交互所需的严格数据结构
# ==========================================
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


# 1. 定义单篇论文的分析结果结构
class PaperAnalysis(BaseModel):
    """用于存储大模型对论文核心要素的提取结果"""

    core_principle: str = Field(
        description="用Markdown格式详细描述该论文的核心原理、算法步骤和数学公式。公式请务必保留LaTeX格式（如 $y = wx + b$）。"
    )

    target_metrics: Dict[str, float] = Field(
        description="论文声称达到的关键实验指标。键为指标名称（如 accuracy, F1, BLEU），值为具体的数字。如果论文没有给出具体数字，请填 0.0。"
    )

    dataset_name: str = Field(
        description="论文使用的核心数据集名称（如 MNIST, CIFAR-10, SQuAD）。如果没有提及，请填 'Unknown'。"
    )

    environment_dependencies: List[str] = Field(
        description="论文中要求必须安装的特定依赖库或框架（如 PyTorch, TensorFlow, CUDA 11.0）。"
    )