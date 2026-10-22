# ==========================================
# workflow.py - LangGraph 终极编排
# ==========================================
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import SciFlowState
from agents import coder_agent, reviewer_agent, critic_agent, human_approval_node
from executor import run_code_in_sandbox


def executor_node(state: SciFlowState):
    res = run_code_in_sandbox(state["task_dir"])
    return {"execution_success": res["success"], "execution_logs": res["logs"]}


def build_workflow():
    workflow = StateGraph(SciFlowState)

    workflow.add_node("coder", coder_agent)
    workflow.add_node("reviewer", reviewer_agent)
    workflow.add_node("approval", human_approval_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("critic", critic_agent)

    workflow.add_edge(START, "coder")
    workflow.add_edge("coder", "reviewer")

    # 静态审查路由
    def route_after_review(state: SciFlowState):
        if state.get("iteration_count", 0) >= 5:
            return "approval"
        if state.get("review_passed"):
            return "approval"
        return "coder"

    workflow.add_conditional_edges("reviewer", route_after_review, {"approval": "approval", "coder": "coder"})

    workflow.add_edge("approval", "executor")
    workflow.add_edge("executor", "critic")

    # 动态评估路由 (触发自进化的核心)
    def route_after_critic(state: SciFlowState):
        if state.get("iteration_count", 0) >= 5:
            print("🚨 达到最大迭代次数，流程结束。")
            return END
        if state.get("review_passed"):
            print("🎉 论文复现成功，指标达标！")
            return END

        print("🔄 指标未达标或运行报错，触发自进化打回重写...")
        return "coder"

    workflow.add_conditional_edges("critic", route_after_critic, {"coder": "coder", END: END})

    return workflow.compile(checkpointer=MemorySaver())