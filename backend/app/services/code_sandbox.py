"""轻量级代码沙箱：在子进程中执行学生代码并验证测试用例输出。"""

import subprocess
import sys
import tempfile
import os
import ast
import threading
from typing import Any


class CodeSandbox:
    TIMEOUT_SECONDS = 5
    MAX_OUTPUT_BYTES = 1_000_000  # 1MB

    DANGEROUS_PATTERNS = [
        "import os", "import sys", "import subprocess", "import shutil",
        "import socket", "import http", "import urllib", "import ftplib",
        "import multiprocessing", "import threading", "import ctypes",
        "import signal", "import pickle", "import marshal", "import importlib",
        "__import__", "eval(", "exec(", "compile(",
        "open(", "os.system", "os.popen", "os.remove", "os.rmdir",
        "os.exec", "os.spawn", "os.fork",
        "shutil.rmtree", "subprocess.Popen", "subprocess.call",
        "getattr(", "setattr(", "delattr(",
        "globals(", "locals(", "vars(",
        "__builtins__", "__subclasses__", "__class__",
        "breakpoint(", "exit(", "quit(",
    ]

    DANGEROUS_JS_PATTERNS = [
        "require('child_process')", "require('fs')", "require('os')",
        "require('net')", "require('http')", "require('https')",
        "require('cluster')", "require('worker_threads')",
        "require('vm')", "require('v8')",
        "process.exit", "process.env", "process.kill",
        "process.binding", "process.dlopen",
        "eval(", "Function(", "setTimeout(", "setInterval(",
        "import(", "globalThis", "global.",
    ]

    # AST 层面检查的危险 Python 节点类型和名称
    DANGEROUS_AST_IMPORTS = {
        "os", "sys", "subprocess", "shutil", "socket", "http", "urllib",
        "ftplib", "multiprocessing", "threading", "ctypes", "signal",
        "pickle", "marshal", "importlib", "pdb", "code", "codeop",
        "compile", "ast", "dis", "inspect",
    }

    DANGEROUS_AST_BUILTINS = {
        "__import__", "eval", "exec", "compile", "breakpoint",
        "exit", "quit", "globals", "locals", "vars",
        "getattr", "setattr", "delattr", "hasattr",
    }

    def _check_safety(self, code: str, language: str) -> str | None:
        """检查代码安全性：字符串匹配 + AST 分析，返回错误信息或 None"""
        # 第一层：字符串模式匹配（快速过滤）
        patterns = self.DANGEROUS_JS_PATTERNS if language == "javascript" else self.DANGEROUS_PATTERNS
        for pattern in patterns:
            if pattern in code:
                return f"代码包含不允许的操作: {pattern}"

        # 第二层：Python AST 分析（深度检查）
        if language == "python":
            ast_error = self._check_ast_safety(code)
            if ast_error:
                return ast_error

        return None

    def _check_ast_safety(self, code: str) -> str | None:
        """通过 AST 分析检查 Python 代码中的危险操作"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None  # 语法错误会在执行阶段被捕获

        for node in ast.walk(tree):
            # 检查危险 import 语句
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_root = alias.name.split(".")[0]
                    if module_root in self.DANGEROUS_AST_IMPORTS:
                        return f"AST 检测到不允许的模块导入: {alias.name}"

            # 检查 from X import ... 形式
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    module_root = node.module.split(".")[0]
                    if module_root in self.DANGEROUS_AST_IMPORTS:
                        return f"AST 检测到不允许的模块导入: {node.module}"

            # 检查 __import__ 和其他危险内建函数调用
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node.func)
                if func_name in self.DANGEROUS_AST_BUILTINS:
                    return f"AST 检测到不允许的函数调用: {func_name}"

            # 检查 __builtins__ 属性访问
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id == "__builtins__":
                    return "AST 检测到不允许的 __builtins__ 访问"

            # 检查 __subclasses__() 等元编程操作
            if isinstance(node, ast.Attribute):
                if node.attr in ("__subclasses__", "__bases__", "__mro__", "__class__"):
                    return f"AST 检测到不允许的元编程操作: .{node.attr}"

        return None

    @staticmethod
    def _get_call_name(func_node) -> str:
        """从 AST 函数调用节点中提取函数名"""
        if isinstance(func_node, ast.Name):
            return func_node.id
        if isinstance(func_node, ast.Attribute):
            return func_node.attr
        return ""

    # 支持的比较模式：exact(精确)、tolerance(浮点容差)、ignore_case(忽略大小写)、ignore_ws(忽略空白差异)
    COMPARE_MODES = {"exact", "tolerance", "ignore_case", "ignore_ws"}

    @staticmethod
    def _compare_outputs(actual: str, expected: str, mode: str = "exact", tolerance: float = 1e-6) -> bool:
        """根据比较模式判断输出是否匹配"""
        if mode == "exact":
            return actual == expected

        if mode == "ignore_case":
            return actual.lower() == expected.lower()

        if mode == "ignore_ws":
            return " ".join(actual.split()) == " ".join(expected.split())

        if mode == "tolerance":
            # 尝试将两个输出按行分割，逐行比较浮点数
            actual_lines = actual.strip().splitlines()
            expected_lines = expected.strip().splitlines()
            if len(actual_lines) != len(expected_lines):
                return False
            for a_line, e_line in zip(actual_lines, expected_lines):
                a_tokens = a_line.strip().split()
                e_tokens = e_line.strip().split()
                if len(a_tokens) != len(e_tokens):
                    return False
                for a_tok, e_tok in zip(a_tokens, e_tokens):
                    try:
                        if abs(float(a_tok) - float(e_tok)) > tolerance:
                            return False
                    except ValueError:
                        if a_tok != e_tok:
                            return False
            return True

        # 未知模式降级为精确比较
        return actual == expected

    def run(self, code: str, language: str, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        """
        执行学生代码并验证测试用例。

        Args:
            code: 学生提交的代码
            language: "python" 或 "javascript"
            test_cases: [{"input": [...], "expected": ..., "compareMode": "exact|tolerance|ignore_case|ignore_ws"}, ...]

        Returns:
            {"passed": int, "total": int, "results": [...], "error": str|None}
        """
        safety_error = self._check_safety(code, language)
        if safety_error:
            return {"passed": 0, "total": len(test_cases), "results": [], "error": safety_error}

        results = []
        passed = 0

        for i, tc in enumerate(test_cases):
            tc_input = tc.get("input", [])
            expected = str(tc.get("expected", "")).strip()
            compare_mode = tc.get("compareMode", "exact")

            try:
                actual = self._execute(code, language, tc_input)
                is_correct = self._compare_outputs(actual, expected, compare_mode)
                if is_correct:
                    passed += 1
                results.append({
                    "testCase": i + 1,
                    "input": tc_input,
                    "expected": expected,
                    "actual": actual,
                    "passed": is_correct,
                    "error": None,
                })
            except TimeoutError:
                results.append({
                    "testCase": i + 1,
                    "input": tc_input,
                    "expected": expected,
                    "actual": "",
                    "passed": False,
                    "error": "执行超时（超过5秒）",
                })
            except Exception as e:
                results.append({
                    "testCase": i + 1,
                    "input": tc_input,
                    "expected": expected,
                    "actual": "",
                    "passed": False,
                    "error": str(e)[:500],
                })

        return {"passed": passed, "total": len(test_cases), "results": results, "error": None}

    def _execute(self, code: str, language: str, inputs: list[str]) -> str:
        """在子进程中执行代码，返回标准输出"""
        input_data = "\n".join(str(x) for x in inputs) + "\n"

        if language == "python":
            cmd = [sys.executable, "-c", code]
        elif language == "javascript":
            cmd = ["node", "-e", code]
        else:
            raise ValueError(f"不支持的语言: {language}")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(input_data)
            input_file = f.name

        proc = None
        try:
            with open(input_file, "r") as stdin_file:
                proc = subprocess.Popen(
                    cmd,
                    stdin=stdin_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=tempfile.gettempdir(),
                )
                stdout_holder: list[bytes] = [b""]
                stderr_holder: list[bytes] = [b""]

                def _read_stdout() -> None:
                    assert proc.stdout is not None
                    data = proc.stdout.read(self.MAX_OUTPUT_BYTES + 1)
                    stdout_holder[0] = data
                    # 超限后立即终止，避免管道写满导致子进程阻塞、wait 超时
                    if len(data) > self.MAX_OUTPUT_BYTES:
                        try:
                            proc.kill()
                        except OSError:
                            pass

                def _read_stderr() -> None:
                    assert proc.stderr is not None
                    stderr_holder[0] = proc.stderr.read(2048)

                t_out = threading.Thread(target=_read_stdout, daemon=True)
                t_err = threading.Thread(target=_read_stderr, daemon=True)
                t_out.start()
                t_err.start()
                timed_out = False
                try:
                    proc.wait(timeout=self.TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    try:
                        proc.kill()
                    except OSError:
                        pass
                    proc.wait()
                finally:
                    t_out.join(timeout=1)
                    t_err.join(timeout=1)

                stdout_bytes = stdout_holder[0]
                stderr_bytes = stderr_holder[0]
                stdout_text = stdout_bytes.decode("utf-8", errors="replace")

                # 输出超限：返回截断结果（即使因 kill 导致非 0 退出码）
                if len(stdout_bytes) > self.MAX_OUTPUT_BYTES:
                    return stdout_text[: self.MAX_OUTPUT_BYTES].strip()

                if timed_out:
                    raise TimeoutError("代码执行超时")

                if proc.returncode != 0:
                    raise RuntimeError(stderr_bytes.decode("utf-8", errors="replace")[:500])
                return stdout_text.strip()
        except subprocess.TimeoutExpired:
            raise TimeoutError("代码执行超时")
        finally:
            if proc is not None:
                if proc.stdout is not None:
                    proc.stdout.close()
                if proc.stderr is not None:
                    proc.stderr.close()
            try:
                os.unlink(input_file)
            except OSError:
                pass
