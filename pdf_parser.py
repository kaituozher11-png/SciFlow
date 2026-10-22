# ==========================================
# pdf_parser.py - 专门负责处理 PDF 解析的模块
# ==========================================
import fitz  # PyMuPDF 的核心模块，用于高效读取 PDF
from pathlib import Path
import json


def parse_pdf_and_save(task_dir: str):
    """
    读取工作区中的 paper.pdf，提取文本和元数据，并保存到工作区。
    返回：提取的结构化数据字典
    """
    # 1. 构建 PDF 的绝对路径（基于第一步生成的工作区）
    pdf_path = Path(task_dir) / "paper.pdf"

    # 安全检查：如果文件不存在，直接报错
    if not pdf_path.exists():
        raise FileNotFoundError(f"找不到 PDF 文件：{pdf_path}")

    # 2. 打开 PDF 文件
    # fitz.open() 返回一个 Document 对象，类似一个列表，里面装着每一页
    doc = fitz.open(pdf_path)

    # 3. 提取基本信息
    total_pages = len(doc)
    metadata = doc.metadata  # 包含作者、标题等

    # 4. 提取全文文本
    full_text = ""
    # 遍历每一页提取文本
    for page_num in range(total_pages):
        page = doc[page_num]
        # get_text() 提取纯文本，"text" 模式会尽量保留段落结构
        page_text = page.get_text("text")

        # 拼接时加上页码标记，方便后续大模型引用出处
        full_text += f"\n\n--- Page {page_num + 1} ---\n\n{page_text}"

    # 5. 简单的文本分块 (Chunking) 准备
    # 为什么分块？因为大模型无法一次性读完超长论文，后续需要用到 RAG 检索
    # 这里我们按字符长度粗分，比如每 2000 个字符一块
    chunk_size = 2000
    chunks = [full_text[i:i + chunk_size] for i in range(0, len(full_text), chunk_size)]

    # 6. 将结果保存到本地文件（持久化）
    # 保存完整文本，供后续大模型概览
    text_save_path = Path(task_dir) / "extracted_text.md"
    with open(text_save_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    # 保存分块数据为 JSON，供 RAG 环节使用
    chunks_save_path = Path(task_dir) / "chunks.json"
    with open(chunks_save_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    # 关闭文档，释放内存
    doc.close()

    # 7. 返回结构化结果
    return {
        "total_pages": total_pages,
        "total_chars": len(full_text),
        "chunks_count": len(chunks),
        "text_file": str(text_save_path)
    }