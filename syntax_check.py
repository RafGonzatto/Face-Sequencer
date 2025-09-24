import ast
import sys

filename = r"c:\Users\Windows 11\Videos\PROJETOOOOOO\im\enhanced_silence_detector.py"

try:
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    
    ast.parse(source, filename)
    print(f"✅ File {filename} has valid Python syntax")
except SyntaxError as e:
    print(f"❌ Syntax error in {filename} at line {e.lineno}, column {e.offset}")
    print(f"Error message: {e.msg}")
    print(f"Line: {e.text.strip()}")
except Exception as e:
    print(f"❌ Error analyzing {filename}: {str(e)}")