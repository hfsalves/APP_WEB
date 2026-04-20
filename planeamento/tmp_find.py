from pathlib import Path
text = Path("i18n.py").read_text(encoding="utf-8")
snippet = "\n        \"production_modal_placeholder\": \"Funcionalidade em desenvolvimento.\",\n        \"assignment_modal_title\""
print(text.find(snippet))
