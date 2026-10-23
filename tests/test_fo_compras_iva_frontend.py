import unittest
from pathlib import Path


class FoComprasIvaFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "static/js/fo_compras_form.js").read_text(encoding="utf-8-sig")

    def test_uses_cent_arithmetic_and_preserves_valid_stored_iva(self):
        self.assertIn("function toCents(value)", self.source)
        self.assertIn("function reconcileStoredIvaWhenReady()", self.source)
        self.assertIn("line.__preserveStoredIva = true;", self.source)
        self.assertIn("Math.abs(storedIva - calculated.ivaCents) > MONEY_EPSILON_CENTS", self.source)

    def test_partial_async_load_does_not_reset_header_totals(self):
        recalc = self.source.split("function recalcTotals()", 1)[1].split("document.addEventListener", 1)[0]
        self.assertIn("if (!isNewRecord && (!headerLoaded || !linesLoaded)) return;", recalc)

    def test_financial_edits_recalculate_the_affected_line(self):
        update = self.source.split("function updateLineField", 1)[1].split("async function saveFo", 1)[0]
        self.assertIn("markLineFinanciallyChanged(line);", update)
        modal_save = self.source.split("async function saveLine()", 1)[1].split("async function deleteLine", 1)[0]
        self.assertIn("const financialChanged", modal_save)
        self.assertIn("if (financialChanged) markLineFinanciallyChanged(merged);", modal_save)

    def test_save_payload_includes_monetary_iva(self):
        normalise = self.source.split("function normalizeLineForSave", 1)[1].split("function recalcModalEtiliq", 1)[0]
        self.assertIn("'ETILIQUIDO', 'IVA', 'TAXAIVA'", normalise)

    def test_render_does_not_unconditionally_replace_existing_line_base(self):
        render = self.source.split("function renderLines()", 1)[1].split("function updateLineField", 1)[0]
        self.assertIn("if (isNewLine(r) || r.__financialDirty) markLineFinanciallyChanged(r);", render)
        self.assertNotIn("r.ETILIQUIDO = (qtt * epv).toFixed(2);", render)


if __name__ == "__main__":
    unittest.main()
