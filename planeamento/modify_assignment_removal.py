import re
from pathlib import Path

path = Path('static/main.js')
text = path.read_text()
pattern = re.compile(r"Object\.keys\(existingStampAssignments\)\.forEach\(\(code\) => {.*?}\s*}\s*\);", re.DOTALL)
match = pattern.search(text)
if not match:
    raise SystemExit('existingStampAssignments block not found via regex')
new_block = "Object.keys(existingStampAssignments).forEach((code) => {\n\n            if (!retainedCodes.has(code)) {\n\n                const removedStamp = existingStampAssignments[code];\n\n                planningData.removePlanStampForAssignment(cell, code);\n\n                if (removedStamp) {\n\n                    if (!planLineCache.has(removedStamp)) {\n\n                        planLineCache.set(removedStamp, []);\n\n                    } else {\n\n                        planLineCache.set(removedStamp, []);\n\n                    }\n\n                    if (!planLineBaselines.has(removedStamp)) {\n\n                        planLineBaselines.set(removedStamp, []);\n\n                    }\n\n                    dirtyPlanLineStamps.add(removedStamp);\n\n                }\n\n                if (removedStamp && cell && cell.dataset && cell.dataset.planLineMap) {\n\n                    let planLineMap;\n\n                    try {\n\n                        planLineMap = JSON.parse(cell.dataset.planLineMap) || {};\n\n                    } catch (error) {\n\n                        planLineMap = {};\n\n                    }\n\n                    if (planLineMap && typeof planLineMap === 'object' && !Array.isArray(planLineMap)\n                        && Object.prototype.hasOwnProperty.call(planLineMap, removedStamp)) {\n\n                        delete planLineMap[removedStamp];\n\n                        if (Object.keys(planLineMap).length) {\n\n                            cell.dataset.planLineMap = JSON.stringify(planLineMap);\n\n                        } else {\n\n                            delete cell.dataset.planLineMap;\n\n                        }\n\n                    }\n\n                }\n\n            }\n\n        });"
text = text[:match.start()] + new_block + text[match.end():]
path.write_text(text)
