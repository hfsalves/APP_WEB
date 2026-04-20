from pathlib import Path

def replace_nth(text, target, replacement, occurrence):
    start = -1
    for _ in range(occurrence + 1):
        start = text.find(target, start + 1)
        if start == -1:
            raise ValueError(f"Target '{target}' occurrence {occurrence} not found")
    end = start + len(target)
    return text[:start] + replacement + text[end:]

path = Path('i18n.py')
text = path.read_text(encoding='utf-8')
pt_block = "        \"planning_week_label\": \"Semana\",\n        \"planning_close_production_button\": \"Fechar Producao\",\n        \"planning_close_production_loading\": \"A fechar producao...\",\n        \"planning_close_production_success\": \"Producao fechada em {count} registos.\",\n        \"planning_close_production_error\": \"Nao foi possivel fechar a producao.\",\n        \"planning_close_production_week_missing\": \"Nao foi possivel determinar a semana ativa.\","\n"
es_block = "        \"planning_week_label\": \"Semana\",\n        \"planning_close_production_button\": \"Cerrar Produccion\",\n        \"planning_close_production_loading\": \"Cerrando produccion...\",\n        \"planning_close_production_success\": \"Produccion cerrada en {count} registros.\",\n        \"planning_close_production_error\": \"No fue posible cerrar la produccion.\",\n        \"planning_close_production_week_missing\": \"No fue posible determinar la semana activa.\","\n"
en_block = "        \"planning_week_label\": \"Week\",\n        \"planning_close_production_button\": \"Close Production\",\n        \"planning_close_production_loading\": \"Closing production...\",\n        \"planning_close_production_success\": \"Production closed on {count} records.\",\n        \"planning_close_production_error\": \"Could not close production.\",\n        \"planning_close_production_week_missing\": \"Active week is unknown.\","\n"
fr_block = "        \"planning_week_label\": \"Semaine\",\n        \"planning_close_production_button\": \"Fermer la production\",\n        \"planning_close_production_loading\": \"Fermeture de la production...\",\n        \"planning_close_production_success\": \"Production fermee sur {count} enregistrements.\",\n        \"planning_close_production_error\": \"Impossible de fermer la production.\",\n        \"planning_close_production_week_missing\": \"Impossible de determiner la semaine active.\","\n"
text = replace_nth(text, '        "planning_week_label": "Semana",', pt_block, 0)
text = replace_nth(text, '        "planning_week_label": "Semana",', es_block, 1)
text = text.replace('        "planning_week_label": "Week",', en_block, 1)
text = text.replace('        "planning_week_label": "Semaine",', fr_block, 1)
path.write_text(text, encoding='utf-8')
