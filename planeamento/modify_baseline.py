from pathlib import Path

path = Path('static/main.js')
text = path.read_text().replace('\r\n', '\n')
marker = "cell.dataset.initialAssignments = cell.dataset.assignments || '[]';"
replacement = "cell.dataset.initialAssignments = cell.dataset.assignments || '[]';\n            cell.dataset.initialPlanStampMap = cell.dataset.planStampMap || '{}' ;"
if marker not in text:
    raise SystemExit('marker not found for initial assignments')
text = text.replace(marker, replacement, 2)
path.write_text(text.replace('\n', '\r\n'))
