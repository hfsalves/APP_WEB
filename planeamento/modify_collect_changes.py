from pathlib import Path

path = Path('static/main.js')
text = path.read_text()
needle = "const initialItems = parseAssignments(cell.dataset.initialAssignments || cell.dataset.assignments);"
if needle not in text:
    raise SystemExit('needle not found')
text = text.replace(needle, needle + "\r\n\r\n            const initialPlanStampMap = parsePlanStampMapPayload(cell.dataset.initialPlanStampMap || cell.dataset.planStampMap) || {};", 1)

old_removal = "            initialCounts.forEach((count, code) => {\r\n\r\n                const current = currentCounts.get(code) || 0;\r\n\r\n                if (count > current) {\r\n\r\n                    for (let index = 0; index < count - current; index += 1) {\r\n\r\n                        removals.push({ date, teamCode: code, projectCode });\r\n\r\n                    }\r\n\r\n                }\r\n\r\n            });"

new_removal = "            initialCounts.forEach((count, code) => {\r\n\r\n                const current = currentCounts.get(code) || 0;\r\n\r\n                if (count > current) {\r\n\r\n                    const planStamp = initialPlanStampMap[code] || '';\r\n\r\n                    for (let index = 0; index < count - current; index += 1) {\r\n\r\n                        removals.push({ date, teamCode: code, projectCode, planStamp });\r\n\r\n                    }\r\n\r\n                }\r\n\r\n            });"

if old_removal not in text:
    raise SystemExit('removal block not found')
text = text.replace(old_removal, new_removal, 1)

path.write_text(text)
