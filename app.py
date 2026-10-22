# ==========================================
# app.py - SciFlow 的主入口与 Web 交互界面 (终极稳定版)
# ==========================================
import streamlit as st
import uuid
from pathlib import Path
from langgraph.types import Command

from pdf_parser import parse_pdf_and_save
from llm_analyzer import analyze_paper_structure
from workflow import build_workflow

st.set_page_config(page_title="SciFlow", page_icon="🧬", layout="wide")
st.title("🧬 SciFlow：自进化论文复现与实验管理")
st.markdown("上传 PDF -> 提取原理 -> 生成代码 -> 审查与沙箱 -> 动态自进化闭环。")


def create_workspace(pdf_file):
    task_id = uuid.uuid4().hex[:8]
    base_dir = Path("workspace") / task_id
    for sub in ["src", "data", "logs"]:
        (base_dir / sub).mkdir(parents=True, exist_ok=True)
    with open(base_dir / "paper.pdf", "wb") as f:
        f.write(pdf_file.getbuffer())
    return task_id, base_dir


uploaded_file = st.file_uploader("请上传 PDF 论文", type=["pdf"])

if uploaded_file is not None:
    st.success(f"已接收文件：{uploaded_file.name}")

    # ==========================================
    # 步骤 1：初始化
    # ==========================================
    if st.button("🚀 1. 初始化工作区并解析 PDF"):
        with st.spinner("正在解析 PDF..."):
            task_id, base_dir = create_workspace(uploaded_file)
            parse_result = parse_pdf_and_save(str(base_dir))
            st.session_state["current_task_dir"] = str(base_dir)
            # 清空之前的状态
            for key in ["core_principle", "target_metrics", "workflow", "thread_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("PDF 解析完成！")

    # ==========================================
    # 步骤 2：大模型分析
    # ==========================================
    if "current_task_dir" in st.session_state:
        st.write("---")
        st.subheader("🧠 核心原理与指标提取")

        # 触发按钮
        if st.button("2. 开始大模型分析"):
            with st.spinner("大模型正在提取中..."):
                analysis_result = analyze_paper_structure(st.session_state["current_task_dir"])
                # 【关键】将结果存入 session_state
                st.session_state["core_principle"] = analysis_result["core_principle"]
                st.session_state["target_metrics"] = analysis_result["target_metrics"]
                st.session_state["dataset_name"] = analysis_result["dataset_name"]
                st.success("论文解析完成！")

        # 【修复】只要 session_state 里有数据，就永远展示它（不依赖按钮状态）
        if "core_principle" in st.session_state:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🎯 目标指标")
                st.json(st.session_state["target_metrics"])
                st.subheader("📦 数据集")
                st.write(st.session_state.get("dataset_name", "Unknown"))
            with col2:
                st.subheader("📐 核心原理")
                # 使用折叠框展示，防止页面太长
                with st.expander("点击查看完整原理", expanded=False):
                    st.markdown(st.session_state["core_principle"])

    # ====================================================
    # 步骤 3 & 4：多智能体编排与沙箱
    # ====================================================
    if "core_principle" in st.session_state:
        st.write("---")
        st.subheader("🤖 多智能体编排与沙箱执行")

        if "workflow" not in st.session_state:
            st.session_state["workflow"] = build_workflow()
            st.session_state["thread_id"] = str(uuid.uuid4())

        workflow = st.session_state["workflow"]
        config = {"configurable": {"thread_id": st.session_state["thread_id"]}}

        # 启动按钮
        if st.button("3. 启动多智能体协作 (包含沙箱执行)"):
            initial_state = {
                "task_dir": st.session_state["current_task_dir"],
                "core_principle": st.session_state["core_principle"],
                "target_metrics": st.session_state["target_metrics"],
                "iteration_count": 0,
                "review_comments": "",
                "review_passed": False,
                "execution_logs": "",
                "execution_success": False
            }

            with st.spinner("多智能体正在协作并执行，请随时查看终端日志（若未过审会自动打回重写）..."):
                try:
                    for event in workflow.stream(initial_state, config=config, stream_mode="updates"):
                        pass
                except Exception as e:
                    st.error(f"图执行过程中出现异常: {e}")
            st.rerun()

        if st.button("🔄 手动同步图状态"):
            st.rerun()

        # 获取图的当前状态
        try:
            state = workflow.get_state(config)

            if not state.values:
                st.info("💡 请点击上方按钮启动多智能体协作流程。")
            else:
                if state.values.get("actual_metrics"):
                    st.info(f"🎯 实际跑出指标：{state.values.get('actual_metrics')}")

                # 1. 检查是否遇到审批节点
                if state.next and "approval" in state.next:
                    interrupt_data = state.tasks[0].interrupts[0].value

                    # 把 AI 的自动审批结果亮出来
                    if state.values.get("review_passed"):
                        st.success("✅ AI Reviewer (自动审查): 代码逻辑初步通过！")

                    st.warning("⚠️ Harness 拦截：等待人工最终审批。是否允许进入 Docker 沙箱？")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("✅ 批准，进入沙箱运行", type="primary"):
                            with st.spinner("恢复图执行，正在启动 Docker... (请观察终端)"):
                                workflow.invoke(Command(resume="approved"), config=config)
                            st.rerun()
                    with col2:
                        if st.button("❌ 拒绝执行"):
                            with st.spinner("拒绝并终止..."):
                                workflow.invoke(Command(resume="rejected"), config=config)
                            st.rerun()

                    with st.expander("📄 点击展开查看生成的完整代码", expanded=False):
                        st.code(interrupt_data["code"], language="python")

                # 2. 检查图是否已结束
                elif not state.next:
                    if state.values.get("review_passed"):
                        st.balloons()
                        st.success("🎉 论文复现成功！指标已对齐。")
                        with st.expander("📄 查看最终可运行的代码", expanded=False):
                            st.code(state.values.get("generated_code"), language="python")
                    else:
                        st.error("❌ 复现失败，达到最大迭代次数或模型无法修复。")
                        st.text_area("最后的沙箱报错日志", state.values.get("execution_logs", "无日志"), height=200)
        except Exception:
            pass