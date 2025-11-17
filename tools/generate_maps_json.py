#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 TypeScript 地图数据转换为 JSON 文件

用法:
    python generate_maps_json.py <ts_file_path>
    
示例:
    python generate_maps_json.py maps.ts
"""
import json
import re
import sys
import argparse
from pathlib import Path


def convert_ts_to_json(ts_code):
    """将 TypeScript 数组代码转换为 JSON"""
    # 移除 TypeScript 特定的语法
    # 1. 移除类型注解和 export
    ts_code = re.sub(r'import.*?;\s*', '', ts_code, flags=re.MULTILINE)
    ts_code = re.sub(r'export const maps:\s*AvaMap\[\]\s*=\s*', '', ts_code)
    ts_code = re.sub(r';\s*$', '', ts_code)
    
    # 2. 先保护字符串内容，避免后续处理时误匹配
    # 存储字符串占位符
    string_placeholders = {}
    placeholder_counter = 0
    
    def protect_strings(match):
        nonlocal placeholder_counter
        placeholder = f'__STRING_{placeholder_counter}__'
        string_placeholders[placeholder] = match.group(0)
        placeholder_counter += 1
        return placeholder
    
    # 先保护所有字符串（单引号和双引号）
    ts_code = re.sub(r'"[^"]*"', protect_strings, ts_code)
    ts_code = re.sub(r"'[^']*'", protect_strings, ts_code)
    
    # 3. 给对象属性名加上引号（处理 name: value 格式）
    def add_quotes_to_keys(match):
        key = match.group(1)
        return f'"{key}":'
    
    # 匹配属性名：标识符后跟冒号（不在字符串内，因为字符串已被保护）
    ts_code = re.sub(r'([a-zA-Z_][a-zA-Z0-9_-]*)\s*:', add_quotes_to_keys, ts_code)
    
    # 4. 恢复字符串内容，并将单引号字符串转换为双引号
    for placeholder, original in string_placeholders.items():
        # 将单引号字符串转换为双引号
        if original.startswith("'") and original.endswith("'"):
            original = '"' + original[1:-1] + '"'
        ts_code = ts_code.replace(placeholder, original)
    
    # 5. 移除尾随逗号
    ts_code = re.sub(r',\s*}', '}', ts_code)
    ts_code = re.sub(r',\s*]', ']', ts_code)
    
    # 6. 使用 json.loads 解析（更安全）
    try:
        data = json.loads(ts_code)
        return data
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        print(f"错误位置: 第 {e.lineno} 行，第 {e.colno} 列")
        # 如果 JSON 解析失败，尝试使用 ast.literal_eval（Python 格式）
        try:
            import ast
            # 将双引号改回单引号用于 Python
            python_code = ts_code.replace('"', "'")
            data = ast.literal_eval(python_code)
            return data
        except Exception as e2:
            print(f"ast 解析也失败: {e2}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description='将 TypeScript 地图数据转换为 JSON 文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python generate_maps_json.py maps.ts
  python generate_maps_json.py path/to/maps.ts
        '''
    )
    parser.add_argument(
        'ts_file',
        type=str,
        help='TypeScript 文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='maps.json',
        help='输出 JSON 文件路径 (默认: maps.json)'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    ts_file_path = Path(args.ts_file)
    if not ts_file_path.exists():
        print(f"错误: 文件不存在: {ts_file_path}")
        sys.exit(1)
    
    # 读取 TypeScript 文件
    try:
        with open(ts_file_path, 'r', encoding='utf-8') as f:
            ts_code = f.read()
    except Exception as e:
        print(f"错误: 无法读取文件 {ts_file_path}: {e}")
        sys.exit(1)
    
    # 转换为 JSON
    maps = convert_ts_to_json(ts_code)
    if maps is None:
        print("错误: 无法解析 TypeScript 代码")
        sys.exit(1)
    
    # 写入 JSON 文件
    output_path = Path(args.output)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(maps, f, indent=2, ensure_ascii=False)
        print(f"✓ 成功生成 {output_path}")
        print(f"✓ 包含 {len(maps)} 个地图数据")
    except Exception as e:
        print(f"错误: 无法写入文件 {output_path}: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

