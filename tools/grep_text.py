import sys
from pathlib import Path

def search(root: Path, needle: str):
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.py', '.html', '.js', '.json', '.ini', '.txt'):
            try:
                txt = p.read_text(encoding='utf-8')
            except Exception:
                try:
                    txt = p.read_text(encoding='cp1252')
                except Exception:
                    continue
            if needle in txt:
                for i, line in enumerate(txt.splitlines(), 1):
                    if needle in line:
                        print(f"{p}:{i}:{line}")

if __name__ == '__main__':
    root = Path('.')
    needle = sys.argv[1] if len(sys.argv) > 1 else 'monitor_tasks'
    search(root, needle)

