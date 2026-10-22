# ==========================================
# agents.py - 终极防呆与双解析引擎版
# ==========================================
import os
import re
import json
import ast  # 新增：用于解析 Python 字典
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langgraph.types import interrupt
from state import SciFlowState
from llm_factory import get_robust_llm

load_dotenv()


# ==========================================
# Agent 1: Coder Agent
# ==========================================
def coder_agent(state: SciFlowState):
    llm = get_robust_llm()
    current_iter = state.get("iteration_count", 0)
    previous_code = state.get("generated_code", "")

    feedback_text = ""
    if state.get("review_comments"):
        feedback_text += f"\n【Reviewer/Critic 评估意见】：\n{state['review_comments']}\n"
    if state.get("execution_logs") and not state.get("execution_success"):
        feedback_text += f"\n【Docker 沙箱运行报错】：\n{state['execution_logs'][-2000:]}\n请务必修复此报错！\n"

    if current_iter > 0:
        print(f"\n🤖 Coder: 接收到重写任务 (第 {current_iter + 1} 次迭代)")

    if current_iter == 0 or not previous_code:
        prompt_content = """你是一个顶级的 AI 算法工程师。请严格根据以下论文原理编写 Python 仿真代码。
        要求：
        1. 严格对齐物理模型和公式。
        2. 必须可以直接运行。
        3. **必须**在代码最后使用 `print(f"[METRICS] {{json.dumps(metrics_dict)}}")` 打印出最终运行的指标。请务必在代码开头 `import json`。
        4. **极其重要：`json` 是 Python 内置库，绝对不能把它写进 requirements.txt 中！** requirements.txt 只写第三方库（如 numpy, scipy）。

        论文原理：
        {principle}

        输出格式：
        ### CODE ###
        (Python代码)
        ### REQUIREMENTS ###
        (只输出第三方库名，不要包含 json, os, sys 等内置库)
        """
    else:
        prompt_content = """你是一个顶级的 AI 算法工程师。上一轮代码未通过，请在【上一次的代码】基础上进行局部修正。

        {feedback}

        论文原理：
        {principle}

        上一次代码：
        {previous_code}

        输出格式：
        ### CODE ###
        (完整修正后的代码，记得 import json 并使用 json.dumps)
        ### REQUIREMENTS ###
        (只输出第三方库，绝不能包含 json)
        """

    prompt = PromptTemplate.from_template(prompt_content)
    response = (prompt | llm).invoke({
        "principle": state["core_principle"],
        "previous_code": previous_code,
        "feedback": feedback_text
    })

    content = response.content
    if isinstance(content, list):
        content = "\n".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in content])
    elif not isinstance(content, str):
        content = str(content)

    try:
        if "### CODE ###" in content and "### REQUIREMENTS ###" in content:
            code_part = content.split("### CODE ###")[1].split("### REQUIREMENTS ###")[0].strip()
            req_part = content.split("### REQUIREMENTS ###")[1].strip()
        else:
            code_match = re.search(r'```python\n(.*?)\n```', content, re.DOTALL)
            code_part = code_match.group(1).strip() if code_match else content
            req_part = "numpy"
    except:
        code_part = content
        req_part = "numpy"

    code_part = code_part.replace("```python", "").replace("```", "").strip()

    # ==========================================================
    # 核心防呆：清洗依赖，并强制拉黑内置库
    # ==========================================================
    built_in_libs = {"json", "os", "sys", "math", "re", "random", "time", "datetime"}
    req_part = req_part.replace("```text", "").replace("```", "")
    valid_lines = []
    for line in req_part.split("\n"):
        line = line.strip().lower()
        if line and not line.startswith("#") and re.match(r'^[a-zA-Z0-9_\-\.><=\s]+$', line):
            # 过滤掉内置库
            if line not in built_in_libs:
                valid_lines.append(line)

    req_part = "\n".join(valid_lines) if valid_lines else "numpy"
    print(f"📦 写入 requirements.txt: {req_part}")

    task_dir = Path(state["task_dir"])
    with open(task_dir / "src" / "main.py", "w", encoding="utf-8") as f:
        f.write(code_part)
    with open(task_dir / "src" / "requirements.txt", "w", encoding="utf-8") as f:
        f.write(req_part)

    return {
        "generated_code": code_part, "requirements_txt": req_part,
        "iteration_count": current_iter + 1, "review_comments": "", "execution_logs": ""
    }


# ==========================================
# Agent 2: Reviewer Agent
# ==========================================
def reviewer_agent(state: SciFlowState):
    llm = get_robust_llm()
    prompt = f"审查以下代码是否有严重语法错误，是否包含 `print(\"[METRICS] ...\")`：\n{state['generated_code']}\n只返回 JSON: {{\"is_pass\": true/false, \"feedback\": \"原因\"}}"
    try:
        content = llm.invoke(prompt).content
        if isinstance(content, list):
            content = "\n".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in content])
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        result_dict = json.loads(json_match.group(0)) if json_match else {"is_pass": True, "feedback": "OK"}
    except:
        result_dict = {"is_pass": True, "feedback": "Review 异常放行"}
    return {"review_passed": result_dict["is_pass"], "review_comments": result_dict["feedback"]}


# ==========================================
# Agent 3: Critic Agent (双引擎解析)
# ==========================================
def critic_agent(state: SciFlowState):
    if not state.get("execution_success"):
        logs = state.get("execution_logs", "")
        error_lines = [line for line in logs.split("\n") if "Error" in line or "Exception" in line]
        error_msg = error_lines[-1] if error_lines else logs.strip().split("\n")[-1]
        return {"review_passed": False, "review_comments": f"运行报错: {error_msg}"}

    logs = state.get("execution_logs", "")
    metrics_match = re.search(r'\[METRICS\]\s*(\{.*\})', logs, re.DOTALL)

    if not metrics_match:
        return {"review_passed": False, "review_comments": "缺失 [METRICS] 打印。"}

    actual_metrics_str = metrics_match.group(1)

    # ==========================================================
    # 核心防呆：双解析引擎 (JSON / Python Dict)
    # ==========================================================
    try:
        actual_dict = json.loads(actual_metrics_str)
    except json.JSONDecodeError:
        # 如果大模型直接打印了字典（单引号），用 ast 兜底解析
        print("⚠️ 检测到非标准 JSON 格式，使用 ast 解析 Python 字典...")
        try:
            actual_dict = ast.literal_eval(actual_metrics_str)
        except Exception as e:
            print(f"❌ 彻底无法解析指标: {e}")
            return {"review_passed": False, "review_comments": "无法解析 [METRICS] 输出。"}

    # 硬性指标检查
    try:
        missed = 0
        if "missed_targets" in actual_dict:
            missed = actual_dict["missed_targets"]
        elif "MSD_ICM" in actual_dict and "missed" in actual_dict["MSD_ICM"]:
            missed = actual_dict["MSD_ICM"]["missed"]
        elif "msd_is" in actual_dict and "missed_targets" in actual_dict["msd_is"]:
            missed = actual_dict["msd_is"]["missed_targets"]

        if missed > 0:
            msg = f"❌ Critic: 算法出现漏检 (missed={missed})。\n"
            msg += "请重点检查论文中的【干扰消除矩阵】和【子空间投影】。请确保正确实现了 MSD-IS 或 MSD-ICM 算法以消除先前检测目标的干扰。"
            print(msg)
            return {"review_passed": False, "review_comments": msg, "actual_metrics": actual_metrics_str}
    except:
        pass

    # 综合大模型评估
    llm = get_robust_llm()
    prompt = f"""
    你是雷达专家。论文目标：{state['target_metrics']}。
    实际指标：{actual_metrics_str}。
    返回 JSON：{{"is_pass": true/false, "feedback": "修改建议"}}
    """

    try:
        content = llm.invoke(prompt).content
        if isinstance(content, list):
            content = "\n".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in content])
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        result_dict = json.loads(json_match.group(0))
    except:
        result_dict = {"is_pass": True, "feedback": "解析异常放行"}

    if not result_dict["is_pass"]:
        print(f"📊 Critic: 指标不达标。打回重写。")
    else:
        print(f"🎉 Critic: 指标达标！")

    return {
        "review_passed": result_dict["is_pass"],
        "review_comments": result_dict.get("feedback", "OK"),
        "actual_metrics": actual_metrics_str
    }


# ==========================================
# Agent 4: Human Approval
# ==========================================
def human_approval_node(state: SciFlowState):
    decision = interrupt({
        "type": "code_approval",
        "code": state["generated_code"],
        "message": "代码已生成，是否进入沙箱？"
    })
    return {"is_approved": decision == "approved"}