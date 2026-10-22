# ==========================================
# state.py - 全局状态定义
# ==========================================
from typing import TypedDict, Dict, List


class SciFlowState(TypedDict):
    task_dir: str
    core_principle: str
    target_metrics: Dict[str, float]

    # Coder 产出
    generated_code: str
    requirements_txt: str

    # Reviewer 产出
    review_passed: bool
    review_comments: str

    # Executor 产出 (沙箱执行结果)
    execution_success: bool
    execution_logs: str  # stdout 和 stderr
    actual_metrics: str  # 从代码输出中提取的指标

    # 控制变量
    iteration_count: int
    is_approved: bool        