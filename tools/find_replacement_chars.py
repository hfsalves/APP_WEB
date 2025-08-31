from pathlib import Path

path = Path('templates/monitor.html')
s = path.read_text(encoding='utf-8', errors='strict')
for i, line in enumerate(s.splitlines(), 1):
    if '\ufffd' in line:
        print(i, line)

