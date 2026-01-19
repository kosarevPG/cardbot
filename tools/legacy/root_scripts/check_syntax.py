#!/usr/bin/env python3
"""Проверка синтаксиса Python файла"""

import sys
import ast

def check_syntax(filename):
    """Проверяет синтаксис Python файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Пытаемся распарсить код
        ast.parse(source)
        print(f"✅ Файл {filename} синтаксически корректен")
        return True
        
    except SyntaxError as e:
        print(f"❌ Синтаксическая ошибка в {filename}:")
        print(f"   Строка {e.lineno}: {e.text}")
        print(f"   Ошибка: {e.msg}")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка при проверке {filename}: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python check_syntax.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    success = check_syntax(filename)
    sys.exit(0 if success else 1)
