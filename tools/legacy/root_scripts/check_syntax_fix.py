#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка синтаксиса main.py
"""
import ast
import sys

def check_syntax(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Парсим AST
        ast.parse(source)
        print(f"✅ Синтаксис {filename} корректен!")
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
    files_to_check = ['main.py', 'modules/settings_menu.py', 'modules/card_of_the_day.py']
    
    all_good = True
    for filename in files_to_check:
        if not check_syntax(filename):
            all_good = False
    
    if all_good:
        print("\n🎉 Все файлы синтаксически корректны!")
        sys.exit(0)
    else:
        print("\n💥 Найдены синтаксические ошибки!")
        sys.exit(1)

