# ==========================================
# 1. 导入所需的标准库和第三方库
# ==========================================
import streamlit as st  # 引入 Streamlit 库，用于快速搭建 Web 界面
import os  # 引入 OS 库，用于与操作系统交互（比如检查文件是否存在）
import uuid  # 引入 UUID 库，用于生成全局唯一的 ID，防止文件夹重名
from pathlib import Path  # 引入 Path 类，这是 Python 现代推荐的路径操作工具，比字符串拼接更安全

# ==========================================
# 2. 页面基础配置 (必须在所有 UI 代码最前面)
# ==========================================
# set_page_config 用于设置浏览器标签页的标题、图标和整体布局
st.set_page_config(
    page_title="SciFlow - 论文复现助手",  # 浏览器标签页的标题
    page_icon="🧬",  # 标签页的小图标（DNA 符号）
    layout="wide"  # 布局模式："wide" 表示使用全屏宽度，避免拥挤
)

# 使用 Markdown 语法渲染页面主标题
st.title("🧬 SciFlow：自进化论文复现与实验管理")
# 渲染一段普通文本作为副标题
st.markdown("上传你的 PDF 论文，系统将为你自动搭建标准化的开发工作区。")


# ==========================================
# 3. 核心业务逻辑函数定义
# ==========================================
def create_workspace(pdf_file):
    """
    接收前端上传的 PDF 文件对象，生成唯一的专属工作区。
    返回：任务ID (task_id) 和工作区绝对路径 (base_dir)
    """
    # 使用 uuid4() 生成一个随机 32 位字符串，截取前 8 位作为任务唯一标识（例如：a1b2c3d4）
    # 为什么要这样做？防止两个用户同时上传，互相覆盖文件
    task_id = uuid.uuid4().hex[:8]

    # 使用 Path 对象拼接路径：workspace/a1b2c3d4
    # 为什么不直接用字符串拼接 "workspace/" + task_id？因为 Path 可以自动处理不同操作系统的路径分隔符（Windows 是 \，Linux 是 /）
    base_dir = Path("workspace") / task_id

    # 定义需要创建的子文件夹列表
    # src: 存放生成的代码 | data: 存放下载的数据 | logs: 存放运行日志
    subdirs = ["src", "data", "logs"]

    # 循环创建子文件夹
    for sub in subdirs:
        # (base_dir / sub) 拼出完整路径
        # mkdir 是创建文件夹；parents=True 表示如果没有 workspace 目录连它一起建；exist_ok=True 表示如果目录已存在不报错
        (base_dir / sub).mkdir(parents=True, exist_ok=True)

    # 指定要保存的 PDF 路径：workspace/a1b2c3d4/paper.pdf
    pdf_path = base_dir / "paper.pdf"

    # 以 "wb" (写入二进制) 模式打开文件，准备写入
    with open(pdf_path, "wb") as f:
        # getbuffer() 是 Streamlit 文件上传器的方法，它把前端上传的文件转成字节流，直接写入本地磁盘
        f.write(pdf_file.getbuffer())

    # 返回生成的 ID 和路径，供外部使用
    return task_id, base_dir


# ==========================================
# 4. 前端 UI 与交互逻辑
# ==========================================
# 在页面上渲染一个文件上传组件
# type=["pdf"] 限制用户只能选择 PDF 文件；如果没有选择，返回值是 None
uploaded_file = st.file_uploader("请上传 PDF 论文", type=["pdf"])

# 如果用户上传了文件（对象不为空）
if uploaded_file is not None:
    # 在页面上弹出一个绿色的成功提示框，显示文件名
    st.success(f"已接收文件：{uploaded_file.name}")

    # 在页面上渲染一个按钮，点击返回 True
    if st.button("🚀 初始化工作区并开始解析"):
        # with 语句用于在页面上显示一个加载动画（转圈圈），提升用户体验
        with st.spinner("正在创建专属工作区..."):
            # 调用上面的函数，真正去磁盘上建文件夹并保存文件
            task_id, base_dir = create_workspace(uploaded_file)

        # 在页面上显示蓝色的信息提示框，展示任务 ID
        st.info(f"✅ 工作区创建成功！任务 ID: `{task_id}`")

        # 在页面上展示一个代码块，显示刚刚建好的文件夹的绝对路径
        st.code(f"文件已保存至: {base_dir.absolute()}")

        # 【关键】将变量存入 st.session_state (Streamlit 的记忆)
        # 因为 Streamlit 每次点击按钮都会重新运行整个脚本，如果不存入 session_state，下一步操作就找不到这个路径了
        st.session_state["current_task_dir"] = str(base_dir)
        st.session_state["current_task_id"] = task_id

        # 打印占位文本，提示下一步开发计划
        st.write("👉 **下一步**：接入大模型解析 PDF（待开发）")