# ==========================================
# executor.py - Docker 安全沙箱执行器 (带日志打印)
# ==========================================
import docker
from pathlib import Path


def run_code_in_sandbox(task_dir: str, timeout_seconds: int = 60) -> dict:
    """
    在 Docker 沙箱中运行生成的代码。
    """
    client = docker.from_env()
    abs_task_dir = str(Path(task_dir).absolute())

    # 组合命令：安装依赖 -> 运行代码 (使用清华源加速)
    command = "pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && python main.py"

    container = None
    try:
        print(f"\n🐳 正在启动 Docker 容器执行代码，挂载目录: {abs_task_dir}")
        # 启动容器
        container = client.containers.run(
            image="python:3.10-slim",
            command=["/bin/sh", "-c", command],
            volumes={abs_task_dir: {'bind': '/app', 'mode': 'rw'}},
            working_dir='/app/src',
            mem_limit="2g",  # 限制内存 2G，防止死循环卡死宿主机
            network_disabled=False,  # 允许网络以进行 pip install
            detach=True,
            stdout=True,
            stderr=True
        )

        # 等待执行完成，设置超时时间
        result = container.wait(timeout=timeout_seconds)
        exit_code = result["StatusCode"]

        # 获取 stdout 和 stderr
        logs = container.logs().decode("utf-8", errors="replace")
        success = (exit_code == 0)

        # 【终端输出】把沙箱里的真实情况打印出来，方便用户观察
        if success:
            print(f"✅ 沙箱执行成功")
            print(f"--- 运行输出 (最后500字) ---\n{logs[-500:]}")
        else:
            print(f"❌ 沙箱执行失败，退出码: {exit_code}")
            print(f"--- 完整报错日志 ---\n{logs}\n----------------")

        return {
            "success": success,
            "logs": logs
        }

    except Exception as e:
        print(f"❌ 沙箱系统异常 (可能超时或 Docker 未启动): {str(e)}")
        return {"success": False, "logs": f"沙箱系统异常: {str(e)}"}
    finally:
        # 核心：无论成功失败，必须强制销毁容器，释放资源！
        if container:
            try:
                container.remove(force=True)
                print("🧹 容器已销毁")
            except:
                pass