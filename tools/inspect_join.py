from pathlib import Path

s = Path('templates/monitor.html').read_text(encoding='utf-8')
for line in s.splitlines():
    if "join('" in line or 'join("' in line or 'H' in line and 'spede' in line:
        print(repr(line))
        # extract between join(' ... ')
        import re
        m = re.search(r"join\((['\"])(.*?)\1\)", line)
        if m:
            sep = m.group(2)
            print('SEP:', sep, 'CODES:', [hex(ord(c)) for c in sep])
        if 'H' in line and 'spede' in line:
            print('CODES LINE:', [hex(ord(c)) for c in line])
