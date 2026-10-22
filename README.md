# 🧬 SciFlow: Self-Evolving Multi-Agent for Paper Reproduction

[English | [简体中文](./README_zh.md)]

SciFlow is a multi-agent system built with **LangGraph**. It takes an academic paper (PDF) as input, automatically extracts core formulas, generates executable code, runs physical simulations in a Docker sandbox, and triggers a **self-evolution loop** based on runtime metrics to perfectly reproduce the paper's results.

## ✨ Key Features
* **Multi-Agent Collaboration**: Coder, Reviewer, and Critic agents interact iteratively to write, review, and evaluate code.
* **Self-Evolution Loop**: Automatically captures sandbox runtime errors, extracts actual metrics, compares them with target metrics, and rewrites code if performance falls short.
* **Long-term Memory**: Utilizes ChromaDB to store historical coding pitfalls and solutions, making the agent smarter with every task.
* **Production-Level Harness**:
  * **Human-in-the-Loop (HITL)**: Mandatory human approval before sandbox execution to prevent unsafe code from running.
  * **Docker Sandbox Isolation**: Executes code in a restricted environment (2GB memory limit) to prevent infinite loops or OOM.
  * **Circuit Breaker**: Limits iteration counts to prevent infinite retry loops and token waste.
* **State Persistence**: Supports `PostgresSaver` for seamless recovery after service restarts.

## 🏗️ Architecture & Workflow
1. **PDF Parsing**: Extracts text and formulas using `PyMuPDF`.
2. **Principle Extraction**: LLM analyzes the text to extract core algorithms and target metrics.
3. **Multi-Agent Generation**: Coder writes code -> Reviewer checks syntax -> **Harness intercepts for Human Approval**.
4. **Execution & Evaluation**: Docker runs the code; Critic evaluates output metrics. If metrics mismatch, it triggers the evolution loop (back to Coder).

## 🚀 Quick Start

### 1. Prerequisites
* Python 3.10+
* Docker Desktop running locally
* API Keys for OpenAI/DeepSeek, etc.

### 2. Installation
```bash
git clone https://github.com/yourusername/SciFlow.git
cd SciFlow
pip install -r requirements.txt