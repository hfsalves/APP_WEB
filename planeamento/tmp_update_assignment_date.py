from pathlib import Path

path = Path('static/main.js')
text = path.read_text()
old_fragment = "                    const assignmentDate = (\r\n\r\n                        sanitizedLine.data\r\n\r\n                        || sanitizedLine.date\r\n\r\n                        || insertion.data\r\n\r\n                        || insertion.date\r\n\r\n                        || activeAssignmentDate\r\n\r\n                        || ''\r\n\r\n                    ).toString().slice(0, 10);\r\n\r\n\r\n\r\n                    const lineItem"
if old_fragment not in text:
    raise SystemExit('assignment fragment not found')
new_fragment = "                    const assignmentDateRaw = (\r\n\r\n                        sanitizedLine.data\r\n\r\n                        || sanitizedLine.date\r\n\r\n                        || insertion.data\r\n\r\n                        || insertion.date\r\n\r\n                        || activeAssignmentDate\r\n\r\n                        || ''\r\n\r\n                    );\r\n\r\n\r\n\r\n                    const assignmentDate = assignmentDateRaw instanceof Date\r\n\r\n                        ? assignmentDateRaw.toISOString().slice(0, 10)\r\n\r\n                        : assignmentDateRaw.toString().slice(0, 10);\r\n\r\n\r\n\r\n                    const lineItem"
text = text.replace(old_fragment, new_fragment, 1)
path.write_text(text)
