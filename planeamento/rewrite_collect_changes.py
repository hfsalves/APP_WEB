from pathlib import Path

path = Path('static/main.js')
text = path.read_text()
start_token = "    const collectChanges = () => {"
start = text.find(start_token)
if start == -1:
    raise SystemExit('collectChanges start not found')
end_token = "    const markSaved = () => {"
end = text.find(end_token, start)
if end == -1:
    raise SystemExit('collectChanges end not found')
collect_block = text[start:end]

replacement = "    const collectChanges = () => {\r\n\r\n        const creations = [];\r\n\r\n        const removals = [];\r\n\r\n        getDayCells().forEach((cell) => {\r\n\r\n            const date = (cell.dataset.date || '').slice(0, 10);\r\n\r\n            const projectCode = (cell.dataset.projectCode || '').trim();\r\n\r\n            if (!date || !projectCode) {\r\n\r\n                return;\r\n\r\n            }\r\n\r\n            const initialItems = parseAssignments(cell.dataset.initialAssignments || cell.dataset.assignments);\r\n\r\n            const currentItems = parseAssignments(cell.dataset.assignments);\r\n\r\n            const initialCounts = countCodes(initialItems);\r\n\r\n            const currentCounts = countCodes(currentItems);\r\n\r\n            const initialPlanStampMap = parsePlanStampMapPayload(cell.dataset.initialPlanStampMap || cell.dataset.planStampMap) || {};\r\n\r\n            currentCounts.forEach((count, code) => {\r\n\r\n                const previous = initialCounts.get(code) || 0;\r\n\r\n                if (count > previous) {\r\n\r\n                    const planStamp = ensurePlanStampForAssignment(cell, code);\r\n\r\n                    for (let index = 0; index < count - previous; index += 1) {\r\n\r\n                        creations.push({ date, teamCode: code, projectCode, planStamp });\r\n\r\n                    }\r\n\r\n                }\r\n\r\n            });\r\n\r\n            initialCounts.forEach((count, code) => {\r\n\r\n                const current = currentCounts.get(code) || 0;\r\n\r\n                if (count > current) {\r\n\r\n                    const planStamp = initialPlanStampMap[code] || '';\r\n\r\n                    for (let index = 0; index < count - current; index += 1) {\r\n\r\n                        removals.push({ date, teamCode: code, projectCode, planStamp });\r\n\r\n                    }\r\n\r\n                }\r\n\r\n            });\r\n\r\n        });\r\n\r\n        return { creations, removals };\r\n\r\n    };\r\n\r\n"

text = text[:start] + replacement + text[end:]

path.write_text(text)
