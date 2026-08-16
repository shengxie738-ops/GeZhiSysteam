"""
格至智能协同教育系统 - 学术报告文档生成主控脚本
生成两份 Word 文档：系统开发说明书 + 测试说明书
最终输出到 D:\gezhisystem\计算机课程知识库\格至文档报告
"""
import os
import sys
import shutil
import time
import traceback

# 确保能导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diagrams import generate_all_diagrams
from dev_spec import build_dev_spec
from test_spec import build_test_spec
from post_process import is_libreoffice_available, update_fields_with_libreoffice


# 最终输出目录
FINAL_OUTPUT_DIR = r'D:\gezhisystem\计算机课程知识库\格至文档报告'


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'output')
    images_dir = os.path.join(output_dir, 'images')

    os.makedirs(images_dir, exist_ok=True)

    # ── 第一步：生成所有图表 ──
    print('=' * 60)
    print('第一步：生成图表（42张）')
    print('=' * 60)
    t0 = time.time()
    try:
        diagram_map = generate_all_diagrams(images_dir)
        print(f'已生成 {len(diagram_map)} 张图表，耗时 {time.time() - t0:.1f}s')
        print(f'图表保存目录：{images_dir}')
    except Exception as e:
        print(f'[错误] 生成图表失败: {e}')
        traceback.print_exc()
        return

    # ── 第二步：生成系统开发说明书 ──
    print()
    print('=' * 60)
    print('第二步：生成系统开发说明书')
    print('=' * 60)
    dev_path = os.path.join(output_dir, '系统开发说明书.docx')
    t1 = time.time()
    try:
        build_dev_spec(dev_path, images_dir)
        print(f'系统开发说明书已生成：{dev_path}')
        print(f'耗时 {time.time() - t1:.1f}s')
        if os.path.exists(dev_path):
            size_mb = os.path.getsize(dev_path) / (1024 * 1024)
            print(f'文件大小：{size_mb:.2f} MB')
    except Exception as e:
        print(f'[错误] 生成系统开发说明书失败: {e}')
        traceback.print_exc()

    # ── 第三步：生成测试说明书 ──
    print()
    print('=' * 60)
    print('第三步：生成测试说明书')
    print('=' * 60)
    test_path = os.path.join(output_dir, '测试说明书.docx')
    t2 = time.time()
    try:
        build_test_spec(test_path, images_dir)
        print(f'测试说明书已生成：{test_path}')
        print(f'耗时 {time.time() - t2:.1f}s')
        if os.path.exists(test_path):
            size_mb = os.path.getsize(test_path) / (1024 * 1024)
            print(f'文件大小：{size_mb:.2f} MB')
    except Exception as e:
        print(f'[错误] 生成测试说明书失败: {e}')
        traceback.print_exc()

    # ── 第四步：LibreOffice 自动更新域（如果可用） ──
    print()
    print('=' * 60)
    print('第四步：LibreOffice 自动更新域')
    print('=' * 60)
    if is_libreoffice_available():
        print('检测到 LibreOffice，开始更新域...')
        for docx_path in [dev_path, test_path]:
            if os.path.exists(docx_path):
                update_fields_with_libreoffice(docx_path)
    else:
        print('未检测到 LibreOffice，跳过自动域更新')
        print('提示：在 Word 中打开文档后，右键目录选择"更新域"即可显示准确页码')

    # ── 第五步：复制到最终输出目录 ──
    print()
    print('=' * 60)
    print('第五步：复制到最终输出目录')
    print('=' * 60)
    print(f'目标目录：{FINAL_OUTPUT_DIR}')

    if not os.path.exists(FINAL_OUTPUT_DIR):
        os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)
        print(f'已创建目录：{FINAL_OUTPUT_DIR}')

    copied_files = []
    for src, name in [(dev_path, '系统开发说明书.docx'), (test_path, '测试说明书.docx')]:
        if os.path.exists(src):
            dst = os.path.join(FINAL_OUTPUT_DIR, name)
            try:
                shutil.copy2(src, dst)
                size_mb = os.path.getsize(dst) / (1024 * 1024)
                print(f'已复制: {name} ({size_mb:.2f} MB)')
                copied_files.append(dst)
            except Exception as e:
                print(f'[错误] 复制 {name} 失败: {e}')

    # ── 汇总 ──
    print()
    print('=' * 60)
    print('全部完成！')
    print('=' * 60)
    print(f'总耗时：{time.time() - t0:.1f}s')
    print()
    print('生成目录（中间产物）:')
    print(f'  {output_dir}')
    print(f'  ├── 系统开发说明书.docx')
    print(f'  ├── 测试说明书.docx')
    print(f'  └── images/ ({len(diagram_map)} 张图表)')
    print()
    print('最终输出目录:')
    print(f'  {FINAL_OUTPUT_DIR}')
    for f in copied_files:
        print(f'  ├── {os.path.basename(f)}')


if __name__ == '__main__':
    main()
