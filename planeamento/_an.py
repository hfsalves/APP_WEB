from pathlib import Path
text = Path('app.py').read_text()
snippet = text.split('return jsonify({\n        "u_planostamp"')[1]
print(repr(snippet[:20]))
