import unittest
from pathlib import Path


class DocumentAiSettingsFrontendTests(unittest.TestCase):
    def test_settings_modal_has_opaque_scoped_panel(self):
        root = Path(__file__).resolve().parents[1]
        css = (root / 'static/css/document_ai.css').read_text(encoding='utf-8')
        template = (root / 'templates/document_ai_inbox.html').read_text(encoding='utf-8')
        self.assertIn('#docAiAccessModal > .docai-access-panel', css)
        self.assertIn('background: var(--sz-color-surface);', css)
        self.assertIn('grid-template-rows: auto auto minmax(0, 1fr) auto;', css)
        self.assertIn('Acessos</button>', template)
        self.assertIn('Informações Obrigatórias</button>', template)
        self.assertIn('Distribuição</button>', template)


if __name__ == '__main__':
    unittest.main()
