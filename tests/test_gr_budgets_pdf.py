from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flask import Flask

from modules.gr_budgets import routes as budget_routes
from modules.gr_budgets.service import (
    _company_logo_path,
    _vat_payload,
    budget_print_payload,
    decorate_budget_browser_pdf,
    render_budget_pdf_html,
)


class BudgetPdfTests(unittest.TestCase):
    def test_phc_bot_uses_euro_columns_before_internal_currency(self):
        tax = _vat_payload(
            {
                "TAXA": Decimal("20"),
                "EBASEINC": Decimal("1069623.24"),
                "BASEINC": Decimal("214440206.40168"),
                "EVALOR": Decimal("213924.65"),
                "VALOR": Decimal("42888041.68130"),
            }
        )
        self.assertEqual(tax["taxable_amount"], 1069623.24)
        self.assertEqual(tax["amount"], 213924.65)

    def _line(self, item, ref, total, quantity=1, price=None, **extra):
        return {
            "bistamp": f"LINE-{item}",
            "item_label": item,
            "reference": ref,
            "designation": f"Designation {item}",
            "description": "ESTE TEXTO BI.DGERAL NÃO DEVE SER IMPRESSO",
            "quantity": Decimal(str(quantity)),
            "unit": "m²",
            "unit_price": Decimal(str(price if price is not None else total)),
            "total": Decimal(str(total)),
            "vat_rate": Decimal("20"),
            "pro_rata": False,
            **extra,
        }

    def _detail_1415(self):
        specs = [
            ("DALLAGE SANS JOINTS SCIEE ENTREPOT - Epaisseur 18 cm", "18063", "42.07", "759910.41"),
            ("DALLAGE ATELIER MAINTENANCE CUR 1,5T/m² - Epaisseur 16 cm", "1997", "37.14", "74168.58"),
            ("PLANCHER ALVEOLAIRES - Epaisseur 7 cm", "839.8", "18.38", "15435.52"),
            ("DALLAGE EXTÉRIEUR AIRE DE BEQUILLAGE ET RAMPES - Epaisseur 18 cm", "3544", "36.29", "128611.76"),
            ("DALLAGE EXTÉRIEUR AIRES BETON BARRIERES ET DE RETOURNEMENT - Epaisseur 21 cm", "1348", "39.04", "52625.92"),
            ("DALLAGE EXTÉRIEUR AIRE VELOS ET TERASSE - Epaisseur 15 cm", "389", "29.95", "11650.55"),
            ("REVÊTEMENT DE SOL LOCAL DE CHARGE", "147", "42.50", "6247.50"),
        ]
        lines = []
        for i, (designation, quantity, price, total) in enumerate(specs, 1):
            line = self._line(str(i), "DTI", total, quantity=quantity, price=price)
            line["designation"] = designation
            line["description"] = designation
            lines.append(line)
        technical = {
            "1": ["Bande de désolidarisation périphérique - épaisseur 1cm", "Film Polyane type 200 microns", "Protection des murs et des poteaux", "Armatures de renfort au niveau des angles rentrants", "JOINT DE CONSTRUCTION SINUSOIDAL", "C 30/37 - XF1 - CEM III - S4", "DURCISSEUR A BASE DE CORINDON", "Finition lissée", "Fibres métalliques BEKAERT à raison de 40 kg/m3", "Protection contre dessication rapide béton par produit cure", "Contrôle béton par un laboratoire indépendant", "COFFRAGE DE RIVES COMPRIS CORNIERES DE RIVES"],
            "2": ["Bande de désolidarisation périphérique - épaisseur 1cm", "Film Polyane type 200 microns", "Protection des murs et des poteaux", "Armatures de renfort au niveau des angles rentrants", "JOINT DE CONSTRUCTION SINUSOIDAL", "C 30/37 - XF1 - CEM III - S4", "DURCISSEUR A BASE DE CORINDON", "Finition lissée", "Fibres métalliques BEKAERT à raison de 40 kg/m3", "Protection contre dessication rapide béton par produit cure", "Contrôle béton par un laboratoire indépendant"],
            "3": ["Protection des murs et des poteaux", "Armatures ST 15C", "Pompage du béton à l’aide d’une pompe", "C 30/37 - XF1 - CEM III - S4", "FINITION LISSE", "Protection contre dessication rapide béton par produit cure"],
            "4": ["Bande de désolidarisation périphérique - épaisseur 1cm", "Film Polyane type 200 microns", "Protection des murs et des poteaux", "Armatures ST 15C", "JOINT DE CONSTRUCTION TYPE PERMABAN", "C 30/37 - XF2 - S4 - Béton extérieur", "FINITION BALAYÉE", "Sciage des joints de retrait", "Protection contre dessication rapide béton par produit cure", "Contrôle béton par un laboratoire indépendant", "COFFRAGE DE RIVES ET COMPRIS FER PLAT EN RIVES"],
            "5": ["Bande de désolidarisation périphérique - épaisseur 1cm", "Film Polyane type 200 microns", "Protection des murs et des poteaux", "Armatures ST 15C", "C 30/37 - XF2 - S3 - Béton extérieur", "FINITION BALAYÉE", "Sciage des joints de retrait", "Protection contre dessication rapide béton par produit cure", "COFFRAGE DE RIVES ET COMPRIS FER PLAZT A L'ENDROIT DE PASSAGES CAMIONS"],
            "6": ["Bande de désolidarisation périphérique - épaisseur 1cm", "Film Polyane type 200 microns", "Protection des murs et des poteaux", "Armatures ST 15C", "C 30/37 - XF2 - S4 - Béton extérieur", "FINITION BALAYÉE", "Protection contre dessication rapide béton par produit cure", "COFFRAGE DE RIVES"],
            "7": ["Grenailleuse; Rabotage; Sablage; Ponçage", "Mise en oeuvre d’un primaire NF EN 13318", "Couche de Masse à raison de 0.100 Kg/m2", "Couche de Finition à raison de 0.100Kg/m2", "Traitement 3 bac de retention", "Compris traitement en peripherique sur 1 metre"],
        }
        for line in lines:
            line["technical_lines"] = [{"designation": text} for text in technical[line["item_label"]]]
        lines.insert(1, self._line("1.1", "PVL", "27094.50", quantity="18063", price="1.50", description="PLUS-VALUE EPAISSEUR 19cm AU LIEU DE 18cm SI NECESSAIRE"))
        lines.append(self._line("PP", "PP", "20973.00", quantity=1, price="20973", pro_rata=True, discount_1=Decimal("2")))
        return {
            "company": {
                "name": "NOME FE NÃO DEVE SER USADO",
                "logo_path": str(Path(__file__).resolve().parents[1] / "storage/fe_logos/GEN00052261619.916000001/logo_57c6f6dca00c.png"),
                "e1": {"name": "H Solutions France SAS", "address": "ZA du Lutzelfeld - Rue de l’Énergie", "postal_code": "F-67870", "city": "GRIESHEIM PRES MOLSHEIM", "country": "FR", "vat_number": "FR46804213593", "phone": "03 68 05 74 65", "email": "accueil@hsols.com", "siret": "80421359300028", "capital": "900.000,00"},
            },
            "header": {"number": 1415, "date": "2026-07-30", "salesperson": "SAID ABDER", "work_name": "Plateforme Logistique", "locality": "MONTOIR DE BRETAGNE", "client_number": 10009, "client_name": "GSE", "address": "310 ALLÉE DE LA CHARTREUSE", "postal_code": "84005", "place": "AVIGNON CEDEX 1", "approved": False},
            "lines": lines,
            "vat_rows": [],
        }

    def test_matches_devis_1415_commercial_totals(self):
        document = budget_print_payload(self._detail_1415())
        self.assertEqual(len(document["articles"]), 7)
        self.assertEqual(len(document["articles"][0]["plus_values"]), 1)
        self.assertEqual(document["articles"][0]["technical_lines"][0]["designation"], "Bande de désolidarisation périphérique - épaisseur 1cm")
        self.assertEqual(document["totals"]["commercial_total"], 1048650.24)
        self.assertEqual(document["totals"]["goods_total"], 1048650.24)
        self.assertEqual(document["totals"]["discount_total"], 0)
        self.assertEqual(document["totals"]["pro_rata_total"], 20973.00)
        self.assertEqual(document["totals"]["net_total"], 1069623.24)
        self.assertEqual(document["totals"]["vat_total"], 213924.65)
        self.assertEqual(document["totals"]["gross_total"], 1283547.89)

    def test_main_item_description_prefers_bi_dgeral(self):
        detail = self._detail_1415()
        detail["lines"][0]["designation"] = "BI.DESIGN - catálogo"
        detail["lines"][0]["description"] = "BI.DGERAL - descrição comercial impressa"

        document = budget_print_payload(detail)
        self.assertEqual(document["articles"][0]["designation"], "BI.DGERAL - descrição comercial impressa")

        app = Flask(__name__, template_folder="../modules/gr_budgets/templates")
        with app.app_context():
            html = render_budget_pdf_html(detail)
        self.assertIn("BI.DGERAL - descrição comercial impressa", html)
        self.assertNotIn("BI.DESIGN - catálogo", html)

    def test_item_thickness_is_appended_in_the_company_language(self):
        french_detail = self._detail_1415()
        french_detail["lines"][0]["description"] = "Dallage industriel"
        french_detail["lines"][0]["thickness"] = Decimal("0.15")
        french_detail["lines"][1]["description"] = "Sous-position"
        french_detail["lines"][1]["thickness"] = Decimal("0.155")

        french_document = budget_print_payload(french_detail)
        self.assertEqual(
            french_document["articles"][0]["designation"],
            "Dallage industriel - Épaisseur 15 cm",
        )

        portuguese_detail = self._detail_1415()
        portuguese_detail["company"]["phc_db"] = "HSOLS_PT"
        portuguese_detail["lines"][0]["description"] = "Pavimento industrial - Epaisseur 12 cm"
        portuguese_detail["lines"][0]["thickness"] = Decimal("0.155")
        portuguese_document = budget_print_payload(portuguese_detail)
        self.assertEqual(
            portuguese_document["articles"][0]["designation"],
            "Pavimento industrial - Espessura 15,5 cm",
        )

        app = Flask(__name__, template_folder="../modules/gr_budgets/templates")
        with app.app_context():
            french_html = render_budget_pdf_html(french_detail)
            portuguese_html = render_budget_pdf_html(portuguese_detail)
        self.assertIn("Dallage industriel - Épaisseur 15 cm", french_html)
        self.assertIn("Pavimento industrial - Espessura 15,5 cm", portuguese_html)

    def test_mvl_prints_as_moins_value_and_pvl_as_plus_value(self):
        detail = self._detail_1415()
        detail["lines"].insert(
            2,
            self._line(
                "1.2",
                "MVL",
                "-4154.49",
                quantity="18063",
                price="-0.23",
                description="JOINT DE CONSTRUCTION DANS LA ZONE DE PREPARATION",
            ),
        )
        document = budget_print_payload(detail)
        self.assertEqual(
            [row["adjustment_label"] for row in document["articles"][0]["plus_values"]],
            ["PLUS-VALUE", "MOINS-VALUE"],
        )

        app = Flask(__name__, template_folder="../modules/gr_budgets/templates")
        with app.app_context():
            html = render_budget_pdf_html(detail)
        self.assertIn(">PLUS-VALUE</span>", html)
        self.assertIn(">MOINS-VALUE</span>", html)

    def test_portuguese_company_uses_portuguese_labels_terms_and_adjustments(self):
        detail = self._detail_1415()
        detail["company"]["phc_db"] = "HSOLS_PT"
        detail["lines"].insert(
            2,
            self._line(
                "1.2",
                "MVL",
                "-4154.49",
                quantity="18063",
                price="-0.23",
                description="MENOR VALIA DE TESTE",
            ),
        )
        detail["lines"].append(self._line("8", "OPT", "0", quantity="10", price="12", option=True))
        detail["lines"].append(
            self._line("9", "VAR", "0", quantity="5", price="10", variant=True, discount_1=Decimal("100"))
        )

        document = budget_print_payload(detail)
        self.assertEqual(document["language"], "pt")
        self.assertEqual(
            [row["adjustment_label"] for row in document["articles"][0]["plus_values"]],
            ["MAIOR-VALIA", "MENOR-VALIA"],
        )
        self.assertEqual(document["articles"][-2]["display_total"], Decimal("120.00"))
        self.assertEqual(document["articles"][-1]["display_total"], Decimal("50.00"))
        self.assertEqual([row["item_label"] for row in document["options"]], ["8"])
        self.assertEqual([row["item_label"] for row in document["variants"]], ["9"])
        self.assertEqual(document["totals"]["commercial_total"], 1048650.24)

        app = Flask(__name__, template_folder="../modules/gr_budgets/templates")
        with app.app_context():
            html = render_budget_pdf_html(detail)
        self.assertIn("Orçamento N.º 1415", html)
        self.assertIn("NÃO APROVADO", html)
        self.assertIn("Vendedor:", html)
        self.assertIn("Morada:", html)
        self.assertIn(">OPÇÃO</span>", html)
        self.assertIn(">ALTERNATIVA</span>", html)
        self.assertIn("120,00", html)
        self.assertIn("50,00", html)
        self.assertIn("class=\"totals-overview\"", html)
        self.assertIn("Descontos:", html)
        self.assertIn("class=\"commercial-choices\"", html)
        self.assertIn("<div class=\"choice-title\">Opções</div>", html)
        self.assertIn("<div class=\"choice-title\">Alternativas</div>", html)
        self.assertIn("CONDIÇÕES GERAIS DE VENDA E DE EXECUÇÃO", html)
        self.assertIn("ARTIGO 17 - CLÁUSULA DE SALVAGUARDA", html)
        self.assertNotIn("CONDITIONS GENERALES DE VENTE ET D´EXECUTION", html)

    def test_zz_designation_is_localized_without_changing_its_value(self):
        french_detail = self._detail_1415()
        french_detail["lines"].append(self._line("8", "OPT", "0", quantity="2", price="75", option=True))
        french_detail["lines"].append(self._line("9", "VAR", "0", quantity="3", price="50", variant=True))
        french_detail["lines"].append(self._line("ZZ", "ZZ", "-250", quantity="-1", price="250"))
        french_document = budget_print_payload(french_detail)
        self.assertEqual(french_document["articles"][-1]["designation"], "ESCOMPTE")
        self.assertEqual(french_document["articles"][-1]["total"], Decimal("-250"))
        app = Flask(__name__, template_folder="../modules/gr_budgets/templates")
        with app.app_context():
            french_html = render_budget_pdf_html(french_detail)
        self.assertIn("Escomptes :", french_html)
        self.assertIn("<div class=\"choice-title\">Options</div>", french_html)
        self.assertIn("<div class=\"choice-title\">Variantes</div>", french_html)

        portuguese_detail = self._detail_1415()
        portuguese_detail["company"]["phc_db"] = "HSOLS_PT"
        portuguese_detail["lines"].append(self._line("ZZ", "", "-250", quantity="-1", price="250"))
        portuguese_document = budget_print_payload(portuguese_detail)
        self.assertEqual(portuguese_document["articles"][-1]["designation"], "DESCONTO")
        self.assertEqual(portuguese_document["articles"][-1]["total"], Decimal("-250"))
        self.assertEqual(portuguese_document["totals"]["goods_total"], 1048650.24)
        self.assertEqual(portuguese_document["totals"]["discount_total"], -250.00)
        self.assertEqual(portuguese_document["totals"]["commercial_total"], 1048400.24)

    def test_html_contains_the_print_model_values(self):
        app = Flask(__name__, template_folder="../modules/gr_budgets/templates")
        with app.app_context():
            html = render_budget_pdf_html(self._detail_1415())
            classic_html = render_budget_pdf_html(self._detail_1415(), "classic")
        self.assertIn("Devis N° 1415", html)
        self.assertIn("NON APPROUVÉ", html)
        self.assertIn("class=\"company-logo\"", html)
        self.assertIn("class=\"company-details\"", html)
        self.assertIn("class=\"address-meta\"", html)
        self.assertIn("class=\"address-lines\"", html)
        self.assertIn("H SOLUTIONS FRANCE SAS", html)
        self.assertNotIn("NOME FE NÃO DEVE SER USADO", html)
        self.assertIn("FR46 804 213 593", html)
        self.assertIn("804 213 593 00028", html)
        self.assertIn("Capital Social : 900.000,00 €", html)
        self.assertIn("class=\"plus-row\"", html)
        self.assertIn("colspan=\"5\"", html)
        self.assertIn("class=\"totals-zone\"", html)
        self.assertIn("signature-in-totals", html)
        self.assertIn("class=\"general-terms-page\"", html)
        self.assertIn("@supports not (position: running(footer))", html)
        self.assertIn(".footer, .continued-header { display: none !important; }", html)
        self.assertIn("CONDITIONS GENERALES DE VENTE ET D´EXECUTION", html)
        self.assertIn("ARTICLE 17 - CLAUSE DE SAUVEGARDE", html)
        self.assertIn("page: general-terms", html)
        self.assertIn("column-count: 3", html)
        self.assertIn(".general-terms-title { color: #fff; background: #303236", html)
        self.assertNotIn(".general-terms-column:nth-child", html)
        self.assertIn("class=\"general-terms-page\"", classic_html)
        self.assertLess(html.index("class=\"totals-zone\""), html.index("class=\"general-terms-page\""))
        self.assertNotIn("signature-in-totals", classic_html)
        self.assertIn("class=\"theme-modern is-unapproved\"", html)
        self.assertIn("class=\"theme-classic is-unapproved\"", classic_html)
        self.assertNotIn("body.theme-modern", classic_html)

    def test_approved_document_uses_compact_header_state(self):
        detail = self._detail_1415()
        detail["header"]["approved"] = True
        app = Flask(__name__, template_folder="../modules/gr_budgets/templates")
        with app.app_context():
            html = render_budget_pdf_html(detail)
        self.assertIn("class=\"theme-modern is-approved\"", html)
        self.assertNotIn("NON APPROUVÉ", html)
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("Bande de désolidarisation périphérique", html)
        self.assertNotIn("ESTE TEXTO BI.DGERAL NÃO DEVE SER IMPRESSO", html)
        self.assertIn("1 069 623,24", html)
        self.assertIn("1 283 547,89", html)

    def test_pdf_endpoint_contract_uses_company_and_bostamp(self):
        app = Flask(__name__)
        user = SimpleNamespace(ADMIN=True, DEV=False, LOGIN="codex")
        detail = {"header": {"number": 1516}}
        with app.test_request_context("/api/gr_orcamentos/orcamento/BO-STAMP/pdf?feid=7&style=modern"):
            with patch.object(budget_routes, "current_user", user), \
                    patch.object(budget_routes, "_has_acl", return_value=True), \
                    patch.object(budget_routes, "get_budget_detail", return_value=detail) as get_detail, \
                    patch.object(budget_routes, "render_budget_pdf_html", return_value="<html></html>") as render_html, \
                    patch.object(
                        budget_routes,
                        "generate_ft_pdf_bytes",
                        return_value=(b"%PDF-test", "weasyprint"),
                    ) as generate_pdf:
                response = budget_routes.api_budget_pdf.__wrapped__("BO-STAMP")

        get_detail.assert_called_once_with("7", "BO-STAMP", user)
        render_html.assert_called_once_with(detail, "modern")
        generate_pdf.assert_called_once_with("<html></html>", return_engine=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertEqual(response.headers["Content-Disposition"], 'inline; filename="Devis_1516.pdf"')
        self.assertEqual(response.headers["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
        self.assertEqual(response.headers["X-PDF-Engine"], "weasyprint")

    def test_browser_pdf_decorator_skips_terms_and_repeats_quote_furniture(self):
        import io

        from pypdf import PdfReader
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        raw_stream = io.BytesIO()
        raw_canvas = canvas.Canvas(raw_stream, pagesize=A4)
        raw_canvas.drawString(72, 760, "QUOTE PAGE 1")
        raw_canvas.showPage()
        raw_canvas.drawString(72, 760, "QUOTE PAGE 2")
        raw_canvas.showPage()
        raw_canvas.drawString(72, 760, "CONDITIONS GENERALES DE VENTE ET D'EXECUTION")
        raw_canvas.save()

        decorated = decorate_budget_browser_pdf(raw_stream.getvalue(), self._detail_1415())
        pages = PdfReader(io.BytesIO(decorated)).pages
        page_text = [page.extract_text() or "" for page in pages]

        self.assertEqual(len(pages), 3)
        self.assertIn("GR 360 Flooring Systems", page_text[0])
        self.assertNotIn("Devis N° 1415", page_text[0])
        self.assertIn("Devis N° 1415", page_text[1])
        self.assertIn("GR 360 Flooring Systems", page_text[1])
        self.assertNotIn("GR 360 Flooring Systems", page_text[2])

    def test_company_logo_never_falls_back_to_another_fe_folder(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            intersol_dir = root / "storage/fe_logos/INTERSOL-STAMP"
            hsols_dir = root / "storage/fe_logos/HSOLS-STAMP"
            intersol_dir.mkdir(parents=True)
            hsols_dir.mkdir(parents=True)
            intersol_logo = intersol_dir / "logo_intersol.png"
            hsols_logo = hsols_dir / "logo_hsols.png"
            intersol_logo.write_bytes(b"intersol")
            hsols_logo.write_bytes(b"hsols")

            resolved = _company_logo_path(
                "INTERSOL-STAMP",
                "storage/fe_logos/HSOLS-STAMP/logo_hsols.png",
                app_root=root,
            )

            self.assertEqual(Path(resolved), intersol_logo.resolve())

    def test_company_without_own_logo_does_not_use_another_company_logo(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            hsols_dir = root / "storage/fe_logos/HSOLS-STAMP"
            hsols_dir.mkdir(parents=True)
            (hsols_dir / "logo_hsols.png").write_bytes(b"hsols")

            resolved = _company_logo_path(
                "INTERSOL-STAMP",
                "storage/fe_logos/HSOLS-STAMP/logo_hsols.png",
                app_root=root,
            )

            self.assertEqual(resolved, "")

    def test_budget_screen_exposes_print_button_and_pdf_url_builder(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")
        self.assertIn('id="budgetPrint"', template)
        self.assertIn("/orcamento/${encodeURIComponent(bostamp)}/pdf", script)
        self.assertIn("selectedFeid !== detailFeid", script)
        self.assertIn("url.searchParams.set('feid', detailFeid)", script)
        self.assertIn("elements.printBudget.addEventListener('click', printBudget)", script)

    def test_budget_screen_exposes_phc_save_button_and_post_action(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")
        self.assertIn('id="budgetCancelEdit"', template)
        self.assertIn('id="budgetSave"', template)
        self.assertIn('id="budgetEdit"', template)
        self.assertIn("await postJson('/orcamento', budgetWritePayload())", script)
        self.assertIn("elements.editBudget.addEventListener('click', startEditBudget)", script)
        self.assertIn("elements.saveBudget.addEventListener('click', saveBudget)", script)

    def test_budget_line_vat_becomes_editable_with_the_budget(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn("gr_budgets.field.vat", template)
        self.assertIn('data-budget-line-vat="${index}"', script)
        start_edit = script.index("function startEditBudget()")
        render_lines = script.index("renderLines(", start_edit)
        render_statuses = script.index("renderStatuses(", start_edit)
        self.assertLess(render_lines, render_statuses)

    def test_technical_line_unit_uses_phc_dytable_options_with_square_metre_default(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")
        service = (root / "modules/gr_budgets/service.py").read_text(encoding="utf-8")

        self.assertIn('<select id="budgetOciUnit" class="sz_select"></select>', template)
        self.assertIn("function populateLineUnitOptions(selectedUnit)", script)
        self.assertIn("const defaultUnit = 'M²';", script)
        self.assertIn("unit: 'M²',", script)
        self.assertIn("populateLineUnitOptions(line.unit || 'M²');", script)
        self.assertIn("populateLineUnitOptions(elements.ociUnit.value || 'M²');", script)
        self.assertIn("UPPER(LTRIM(RTRIM(ISNULL(ENTITYNAME, '')))) = 'ST_UNIDADE'", service)

    def test_budget_and_position_duplication_controls_are_available(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn('id="budgetDuplicate"', template)
        self.assertIn('id="budgetActionsMenu"', template)
        self.assertIn('id="budgetActionsToggle"', template)
        self.assertIn('id="budgetOciDuplicate"', template)
        self.assertIn('id="budgetPositionDuplicateConfirm"', template)
        self.assertIn("function startDuplicateBudget()", script)
        self.assertIn("function duplicatePosition(lineIndex)", script)
        self.assertIn("function requestGridPositionDuplicate(lineIndex)", script)
        self.assertIn("function saveAndDuplicateCurrentPosition()", script)
        self.assertIn("lines: cloneBudgetLinesForDraft(sourceDetail.lines || [])", script)
        self.assertIn("const newPosition = nextBudgetPosition();", script)
        self.assertIn("elements.actionsMenu.hidden = editing", script)
        self.assertIn("data-tooltip=", script)
        self.assertIn("elements.positionDuplicateSave.addEventListener('click', confirmPositionDuplicate)", script)

    def test_grid_line_actions_are_at_the_end_and_delete_is_confirmed(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn('id="budgetLineDeleteConfirm"', template)
        self.assertIn('data-delete-line="${index}"', script)
        self.assertIn("function requestBudgetLineDelete(lineIndex)", script)
        self.assertIn("function confirmBudgetLineDelete()", script)
        self.assertIn("label.startsWith(prefix)", script)
        profit_cell = script.index('Number(line.profit || 0)')
        action_cell = script.index('gr-budget-line-actions-column', profit_cell)
        self.assertGreater(action_cell, profit_cell)

    def test_budget_grid_keeps_unit_and_technical_columns_readable(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")
        styles = (root / "modules/gr_budgets/static/gr_budgets.css").read_text(encoding="utf-8")

        self.assertIn('class="gr-budget-col-unit"', template)
        self.assertIn('<td class="gr-budget-col-unit">', script)
        self.assertIn(".gr-budget-col-unit {", styles)
        self.assertIn("width: 4.75rem;", styles)
        self.assertIn("text-overflow: clip !important;", styles)

    def test_duplicate_lines_receive_new_draft_identifiers(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn("bistamp = newDraftId('line')", script)
        self.assertIn("stamp: newDraftId('oci')", script)
        self.assertIn("budget_stamp: ''", script)
        self.assertIn("line_stamp: newLineStamp", script)

    def test_budget_commercial_adjustments_are_available(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn('id="budgetFinalPrice"', template)
        self.assertIn('id="budgetDiscount"', template)
        self.assertIn('id="budgetCommercialAdjustment"', template)
        self.assertIn("function applyCommercialAdjustment()", script)
        self.assertIn("baseTotal * value / 100", script)
        self.assertIn("baseTotal - value", script)
        self.assertIn("order: 999999999", script)
        self.assertIn("item_label: 'ZZ'", script)
        self.assertIn("designation: 'ESCOMPTE'", script)
        self.assertIn("quantity: -1", script)
        self.assertIn("filter((line) => !isBudgetDiscountLine(line))", script)

    def test_budget_can_apply_one_vat_rate_to_all_lines(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn('id="budgetApplyVat"', template)
        self.assertIn('id="budgetVatApply"', template)
        self.assertIn('id="budgetVatApplySelect"', template)
        self.assertIn("function applyVatToAllLines()", script)
        self.assertIn("state.detail.header.default_vat_table = vatTable", script)
        self.assertIn("state.detail.header.default_vat_rate = vatRate", script)
        self.assertIn("line.vat_table = vatTable", script)
        self.assertIn("line.vat_rate = vatRate", script)
        self.assertIn("elements.applyVatBudget.addEventListener('click', openVatApply)", script)

    def test_client_without_vat_table_uses_the_application_default(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn("rates.find((rate) => Number(rate.table || 0) === requestedVatTable)", script)
        self.assertIn("rates.find((rate) => Number(rate.table || 0) === 2)", script)

    def test_budget_approval_action_and_confirmation_are_available(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn('id="budgetApproval"', template)
        self.assertIn('id="budgetApprovalConfirm"', template)
        self.assertIn("function openApprovalConfirm()", script)
        self.assertIn("function applyBudgetApproval()", script)
        self.assertIn("/aprovacao`,", script)
        self.assertIn("elements.approvalBudget.addEventListener('click', openApprovalConfirm)", script)

    def test_approval_endpoint_uses_edit_acl_and_authenticated_user(self):
        app = Flask(__name__)
        user = SimpleNamespace(ADMIN=True, DEV=False, LOGIN="codex")
        result = {"bostamp": "BUDGET-1", "approved": True, "credit": {"available": 10}}
        with app.test_request_context(
            "/api/gr_orcamentos/orcamento/BUDGET-1/aprovacao",
            method="POST",
            json={"feid": 7, "approved": True},
        ):
            with patch.object(budget_routes, "current_user", user), \
                    patch.object(budget_routes, "_has_write_acl", return_value=True) as acl, \
                    patch.object(budget_routes, "set_budget_approval", return_value=result) as approve:
                response = budget_routes.api_budget_approval.__wrapped__("BUDGET-1")

        acl.assert_called_once_with(False)
        approve.assert_called_once_with(7, "BUDGET-1", True, user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["approved"])

    def test_new_budget_header_is_kept_when_returning_from_technical_detail(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")
        self.assertIn("function syncEditableHeaderToState()", script)
        open_oci = script.index("async function openOci(lineIndex, newLine)")
        sync_header = script.index("syncEditableHeaderToState();", open_oci)
        start_loading = script.index("showLoading(true);", open_oci)
        self.assertLess(sync_header, start_loading)
        self.assertIn("syncEditableHeaderToState();\n    closeClientLookup();", script)

    def test_budget_line_money_is_presented_with_two_decimals(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "modules/gr_budgets/templates/gr_budgets/budgets.html").read_text(encoding="utf-8")
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")
        self.assertIn("minimumFractionDigits: 2, maximumFractionDigits: 2", script)
        self.assertIn("roundMoney(row.purchase_price).toFixed(2)", script)
        self.assertIn('id="budgetOciSalePrice"', template)
        self.assertIn('min="0" step="0.01"', template)

    def test_oci_purchase_price_accepts_localized_decimals_and_is_committed_before_save(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "modules/gr_budgets/static/gr_budgets.js").read_text(encoding="utf-8")

        self.assertIn("function parseLocalizedNumber(rawValue)", script)
        self.assertIn('data-oci-field="purchase_price" data-oci-numeric', script)
        self.assertIn('type="text" inputmode="decimal"', script)
        self.assertIn("function commitOciNumericInputs()", script)
        save_line = script.index("function saveOciLine()")
        commit = script.index("commitOciNumericInputs();", save_line)
        recalculate = script.index("recalculateOci();", commit)
        collect = script.index("const rows = collectOciRows();", recalculate)
        self.assertLess(commit, recalculate)
        self.assertLess(recalculate, collect)
        self.assertIn("base_purchase_price: roundMoney(row.dataset.ociBasePurchasePrice)", script)

    def test_save_endpoint_uses_write_acl_and_authenticated_user(self):
        app = Flask(__name__)
        user = SimpleNamespace(ADMIN=True, DEV=False, LOGIN="codex")
        saved = {"created": True, "bostamp": "NEW-STAMP", "number": 1620, "year": 2026}
        with app.test_request_context(
            "/api/gr_orcamentos/orcamento",
            method="POST",
            json={"feid": 7, "ndos": 115, "header": {"client_number": 1}},
        ):
            with patch.object(budget_routes, "current_user", user), \
                    patch.object(budget_routes, "_has_write_acl", return_value=True) as acl, \
                    patch.object(budget_routes, "save_budget", return_value=saved) as save:
                response = budget_routes.api_save_budget.__wrapped__()

        acl.assert_called_once_with(True)
        save.assert_called_once_with({"feid": 7, "ndos": 115, "header": {"client_number": 1}}, user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["bostamp"], "NEW-STAMP")


if __name__ == "__main__":
    unittest.main()
