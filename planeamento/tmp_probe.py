from pathlib import Path
text = Path("i18n.py").read_text(encoding="utf-8")
print(text[5700:5980])
