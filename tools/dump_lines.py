import sys
from pathlib import Path

def dump(path, start=None, end=None, needle=None):
    p = Path(path)
    data = p.read_text(encoding='utf-8', errors='ignore').splitlines()
    if needle:
        for i, line in enumerate(data, 1):
            if needle in line:
                print(f"{i:5}: {line}")
        return
    s = max(1, int(start or 1))
    e = min(len(data), int(end or len(data)))
    for i in range(s, e+1):
        print(f"{i:5}: {data[i-1]}")

if __name__ == '__main__':
    # Usage: python tools/dump_lines.py file [start] [end]
    # or:    python tools/dump_lines.py file find <needle>
    if len(sys.argv) < 2:
        print('usage: dump_lines.py <file> [start] [end] | find <needle>')
        sys.exit(1)
    file = sys.argv[1]
    if len(sys.argv) >= 3 and sys.argv[2] == 'find':
        dump(file, needle=' '.join(sys.argv[3:]))
    else:
        start = int(sys.argv[2]) if len(sys.argv) >= 3 else None
        end = int(sys.argv[3]) if len(sys.argv) >= 4 else None
        dump(file, start, end)

