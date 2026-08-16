"""
后处理脚本：调用 LibreOffice headless 模式更新 docx 中所有域
（目录页码、交叉引用等）

用法：
    python post_process.py <docx_path> [docx_path2 ...]
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_soffice() -> str:
    """查找 soffice 可执行文件路径"""
    # Windows 常见路径
    win_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in win_paths:
        if os.path.exists(p):
            return p

    # PATH 中查找
    found = shutil.which('soffice') or shutil.which('libreoffice')
    if found:
        return found

    # macOS
    mac_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if os.path.exists(mac_path):
        return mac_path

    return None


def is_libreoffice_available() -> bool:
    """检测系统是否安装 LibreOffice (soffice 命令)"""
    return find_soffice() is not None


def update_fields_with_libreoffice(docx_path: str, timeout: int = 120) -> bool:
    """
    调用 LibreOffice headless 模式更新 docx 中所有域

    采用方案C：用 soffice --convert-to docx 重新转换。
    转换过程中 LibreOffice 会自动更新所有域，然后将转换后的文件替换原文件。

    返回 True 表示成功，False 表示失败
    """
    soffice = find_soffice()
    if not soffice:
        print("[post_process] 未检测到 LibreOffice，跳过域更新")
        print("[post_process] 提示：在 Word 中打开文档后，右键目录选择'更新域'即可显示准确页码")
        return False

    docx_path = os.path.abspath(docx_path)
    if not os.path.exists(docx_path):
        print(f"[post_process] 文件不存在: {docx_path}")
        return False

    # 创建临时目录
    with tempfile.TemporaryDirectory(prefix='lo_update_') as temp_dir:
        print(f"[post_process] 调用 LibreOffice 更新域: {docx_path}")

        cmd = [
            soffice,
            '--headless',
            '--norestore',
            '--nologo',
            '--nofirststartwizard',
            '--convert-to', 'docx:"MS Word 2007 XML"',
            '--outdir', temp_dir,
            docx_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

            if result.returncode != 0:
                print(f"[post_process] LibreOffice 转换失败 (exit {result.returncode})")
                if result.stderr:
                    print(f"[post_process] stderr: {result.stderr[:500]}")
                return False

            # 查找转换后的文件
            converted_file = os.path.join(temp_dir, os.path.basename(docx_path))
            if not os.path.exists(converted_file):
                print(f"[post_process] 转换后文件未找到: {converted_file}")
                return False

            # 复制回原路径
            shutil.copy2(converted_file, docx_path)
            print(f"[post_process] 域更新完成: {docx_path}")
            return True

        except subprocess.TimeoutExpired:
            print(f"[post_process] LibreOffice 转换超时（{timeout}s）")
            return False
        except Exception as e:
            print(f"[post_process] 调用 LibreOffice 出错: {e}")
            return False


def update_fields_batch(docx_paths: list, timeout_per_file: int = 120) -> dict:
    """
    批量更新多个 docx 文件的域

    返回 {文件路径: 是否成功}
    """
    results = {}
    for path in docx_paths:
        results[path] = update_fields_with_libreoffice(path, timeout_per_file)
    return results


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python post_process.py <docx_path> [docx_path2 ...]")
        sys.exit(1)

    paths = sys.argv[1:]
    print(f"待更新文件: {paths}")

    if not is_libreoffice_available():
        print("未检测到 LibreOffice，无法自动更新域")
        print("请安装 LibreOffice: https://www.libreoffice.org/download/")
        sys.exit(1)

    results = update_fields_batch(paths)
    print("\n更新结果:")
    for path, success in results.items():
        status = "成功" if success else "失败"
        print(f"  {path}: {status}")
