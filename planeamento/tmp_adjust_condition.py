from pathlib import Path

path = Path('static/main.js')
text = path.read_text()
old_cond = "                        !normalizedPlanStamp\r\r\n\r\r\n                        || !planBistamp\r\r\n\r\r\n                        || !lineItem\r\r\n\r\r\n                        || !normalizedTeamCode\r\r\n\r\r\n                        || !normalizedProjectCode\r\r\n\r\r\n                        || !assignmentDate\r\r\n\r\r\n                    ) {"
if old_cond not in text:
    raise SystemExit('condition snippet not found')
new_cond = "                        !normalizedPlanStamp\r\n\r\n                        || !planBistamp\r\n\r\n                        || lineItem === null\r\n\r\n                        || !normalizedTeamCode\r\n\r\n                        || !normalizedProjectCode\r\n\r\n                        || !assignmentDate\r\n\r\n                    ) {"
text = text.replace(old_cond, new_cond, 1)
path.write_text(text)
