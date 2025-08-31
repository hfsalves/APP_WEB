import sys
from pathlib import Path

def fix_text(text: str) -> str:
    # Corrige mojibake típico: texto UTF-8 que foi decodificado como latin-1/cp1252
    try:
        # Usa cp1252 (Windows-1252) para preservar € e outros símbolos
        fixed = text.encode('cp1252', errors='ignore').decode('utf-8', errors='ignore')
    except Exception:
        return text
    return fixed

def process_file(path: Path) -> bool:
    original = path.read_text(encoding='utf-8', errors='ignore')
    fixed = fix_text(original)
    if fixed != original:
        path.write_text(fixed, encoding='utf-8')
        return True
    return False

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python tools/fix_mojibake.py <file1> [file2 ...]")
        return 2
    changed_any = False
    for arg in argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"[skip] {arg} (not found)")
            continue
        changed = process_file(p)
        print(f"[{'fixed' if changed else 'ok   '}] {arg}")
        changed_any = changed_any or changed
    return 0 if changed_any else 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
