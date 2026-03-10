from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text

from models import db


_DEC2 = Decimal("0.01")
_PRODUCT_TRANSLATION_COLUMNS = (
    "NOME_EN",
    "NOME_ES",
    "NOME_FR",
    "TITULO_EN",
    "TITULO_ES",
    "TITULO_FR",
    "SUBTITULO_EN",
    "SUBTITULO_ES",
    "SUBTITULO_FR",
    "DESCRICAO_CURTA_EN",
    "DESCRICAO_CURTA_ES",
    "DESCRICAO_CURTA_FR",
    "DESCRICAO_EN",
    "DESCRICAO_ES",
    "DESCRICAO_FR",
)

_FAMILY_UI_META = {
    "MAIS_POPULARES": {"icon": "fa-fire-flame-curved", "accent": "#f59e0b"},
    "PEQUENO_ALMOCO": {"icon": "fa-mug-hot", "accent": "#f97316"},
    "MERCEARIA": {"icon": "fa-basket-shopping", "accent": "#84cc16"},
    "BEBIDAS": {"icon": "fa-wine-bottle", "accent": "#06b6d4"},
    "HIGIENE_PESSOAL": {"icon": "fa-pump-soap", "accent": "#8b5cf6"},
    "SURPRESAS": {"icon": "fa-gift", "accent": "#ec4899"},
    "UTILITARIOS": {"icon": "fa-suitcase-medical", "accent": "#64748b"},
    "ADULT_MATERIAL": {"icon": "fa-moon", "accent": "#be185d"},
}


_SHOP_FAMILIES = [
    {
        "code": "MAIS_POPULARES",
        "name": "Mais populares",
        "title": "Mais populares",
        "description": "Sugestoes simples para melhorar a chegada.",
        "sort_order": 10,
        "icon": "fa-fire-flame-curved",
        "accent": "#f59e0b",
    },
    {
        "code": "PEQUENO_ALMOCO",
        "name": "Pequeno almoco",
        "title": "Pequeno almoco",
        "description": "Essenciais para a primeira manha.",
        "sort_order": 20,
        "icon": "fa-mug-hot",
        "accent": "#f97316",
    },
    {
        "code": "MERCEARIA",
        "name": "Mercearia",
        "title": "Mercearia",
        "description": "Base pratica de despensa e cozinha.",
        "sort_order": 30,
        "icon": "fa-basket-shopping",
        "accent": "#84cc16",
    },
    {
        "code": "BEBIDAS",
        "name": "Bebidas",
        "title": "Bebidas",
        "description": "Agua, sumos, vinho e mixers.",
        "sort_order": 40,
        "icon": "fa-wine-bottle",
        "accent": "#06b6d4",
    },
    {
        "code": "HIGIENE_PESSOAL",
        "name": "Higiene pessoal",
        "title": "Higiene pessoal",
        "description": "Pequenos essenciais de conforto.",
        "sort_order": 50,
        "icon": "fa-pump-soap",
        "accent": "#8b5cf6",
    },
    {
        "code": "SURPRESAS",
        "name": "Surpresas",
        "title": "Surpresas",
        "description": "Detalhes para tornar a estadia memoravel.",
        "sort_order": 60,
        "icon": "fa-gift",
        "accent": "#ec4899",
    },
    {
        "code": "UTILITARIOS",
        "name": "Utilitarios",
        "title": "Utilitarios",
        "description": "Itens praticos para imprevistos de viagem.",
        "sort_order": 70,
        "icon": "fa-suitcase-medical",
        "accent": "#64748b",
    },
    {
        "code": "ADULT_MATERIAL",
        "name": "Adult material",
        "title": "Adult material",
        "description": "Artigos discretos de bem-estar adulto.",
        "sort_order": 80,
        "icon": "fa-moon",
        "accent": "#be185d",
    },
]


_SHOP_PRODUCTS = [
    {"code": "POP_AGUA_6X33", "family_code": "MAIS_POPULARES", "name": "Agua mineral 6x33cl", "subtitle": "Pack compacto para chegada", "description_short": "Seis garrafas pequenas prontas para o primeiro dia.", "description": "Pack com seis garrafas de agua mineral natural. Ideal para ter agua fresca disponivel logo a chegada.", "price": "2.90", "sort_order": 10},
    {"code": "POP_LEITE_PAO", "family_code": "MAIS_POPULARES", "name": "Kit leite e pao", "subtitle": "Basico para a primeira manha", "description_short": "Leite meio-gordo e pao de forma para uma chegada tranquila.", "description": "Combinacao simples para quem chega tarde e quer assegurar pequeno-almoco sem sair de casa.", "price": "3.80", "sort_order": 20},
    {"code": "POP_CAFE_CAPS", "family_code": "MAIS_POPULARES", "name": "Capsulas de cafe x10", "subtitle": "Compativel Nespresso", "description_short": "Dez capsulas para o primeiro cafe da estadia.", "description": "Cafe pratico, intenso e facil para uma primeira pausa depois do check-in.", "price": "4.50", "sort_order": 30},
    {"code": "POP_VINHO_TINTO", "family_code": "MAIS_POPULARES", "name": "Vinho tinto regional 75cl", "subtitle": "Selecao regional", "description_short": "Uma garrafa equilibrada para receber bem.", "description": "Vinho tinto portugues de perfil suave, pensado para harmonizar com uma chegada relaxada.", "price": "7.90", "sort_order": 40},
    {"code": "POP_CHIPS_SNACK", "family_code": "MAIS_POPULARES", "name": "Batatas fritas gourmet", "subtitle": "Snack salgado", "description_short": "Embalagem partilhavel e crocante.", "description": "Snack rapido para acompanhar bebidas e descontrair apos a viagem.", "price": "2.40", "sort_order": 50},
    {"code": "POP_HIGIENE_SET", "family_code": "MAIS_POPULARES", "name": "Kit higiene express", "subtitle": "Escova, pasta e gel", "description_short": "Essenciais de higiene para esquecimentos de ultima hora.", "description": "Conjunto compacto com basicos de higiene pessoal, pensado para bagagem leve ou imprevistos.", "price": "5.90", "sort_order": 60},

    {"code": "PA_LEITE_1L", "family_code": "PEQUENO_ALMOCO", "name": "Leite meio-gordo 1L", "subtitle": "Formato familiar", "description_short": "Leite UHT para cafe, cereais ou pequeno-almoco.", "description": "Essencial versatil para pequenos-almocos simples e refeicoes leves.", "price": "1.35", "sort_order": 10},
    {"code": "PA_OVOS_6", "family_code": "PEQUENO_ALMOCO", "name": "Ovos classe M x6", "subtitle": "Caixa de 6 ovos", "description_short": "Uma base pratica para omeletes ou ovos mexidos.", "description": "Caixa com seis ovos frescos, ideal para preparar uma refeicao rapida logo de manha.", "price": "2.10", "sort_order": 20},
    {"code": "PA_PAO_FORMA", "family_code": "PEQUENO_ALMOCO", "name": "Pao de forma integral", "subtitle": "Fatiado e versatil", "description_short": "Torradas e sandes sem complicacoes.", "description": "Pao de forma integral fatiado, pronto para torradas ou sandes leves.", "price": "1.95", "sort_order": 30},
    {"code": "PA_MANTEIGA_250", "family_code": "PEQUENO_ALMOCO", "name": "Manteiga 250g", "subtitle": "Bloco refrigerado", "description_short": "Manteiga tradicional para barrar ou cozinhar.", "description": "Manteiga com sal, versatil para pequeno-almoco e cozinha do dia a dia.", "price": "2.45", "sort_order": 40},
    {"code": "PA_COMPOTA_30", "family_code": "PEQUENO_ALMOCO", "name": "Compota de morango x4", "subtitle": "Doses individuais", "description_short": "Formato pratico, sem desperdicio.", "description": "Conjunto com quatro doses individuais de compota, ideal para pequeno-almoco de chegada.", "price": "2.20", "sort_order": 50},
    {"code": "PA_CEREAIS_375", "family_code": "PEQUENO_ALMOCO", "name": "Cereais crocantes 375g", "subtitle": "Formato standard", "description_short": "Uma opcao rapida para adultos e criancas.", "description": "Cereais crocantes para servir com leite ou iogurte, prontos para a primeira manha.", "price": "3.25", "sort_order": 60},

    {"code": "MER_ARROZ_1KG", "family_code": "MERCEARIA", "name": "Arroz agulha 1kg", "subtitle": "Base de refeicao", "description_short": "Produto essencial para varias refeicoes.", "description": "Arroz agulha de grao longo, facil de cozinhar e util para estadias com cozinha ativa.", "price": "2.10", "sort_order": 10},
    {"code": "MER_MASSA_500", "family_code": "MERCEARIA", "name": "Massa esparguete 500g", "subtitle": "Formato classico", "description_short": "Refeicao rapida e sem complexidade.", "description": "Esparguete de trigo duro em embalagem de 500g, ideal para refeicoes simples.", "price": "1.45", "sort_order": 20},
    {"code": "MER_ATUM_3X", "family_code": "MERCEARIA", "name": "Atum em azeite x3", "subtitle": "Pack de 3 latas", "description_short": "Pronto para saladas, massas ou lanches.", "description": "Tres latas de atum em azeite para refeicoes praticas durante a estadia.", "price": "3.90", "sort_order": 30},
    {"code": "MER_AZEITE_75", "family_code": "MERCEARIA", "name": "Azeite virgem extra 75cl", "subtitle": "Produto local", "description_short": "Essencial de cozinha com perfil portugues.", "description": "Azeite virgem extra para cozinhar e temperar, com perfil versatil e local.", "price": "6.90", "sort_order": 40},
    {"code": "MER_SAL_1KG", "family_code": "MERCEARIA", "name": "Sal fino 1kg", "subtitle": "Uso diario", "description_short": "Basico de despensa para cozinhar.", "description": "Sal fino alimentar em formato standard para utilizacao pratica durante a estadia.", "price": "0.85", "sort_order": 50},
    {"code": "MER_ACUCAR_1KG", "family_code": "MERCEARIA", "name": "Acucar branco 1kg", "subtitle": "Formato familiar", "description_short": "Para cafe, cha e pequenas preparacoes.", "description": "Acucar branco em embalagem de 1kg para uso diario na cozinha.", "price": "1.20", "sort_order": 60},

    {"code": "BEB_AGUA_1L5", "family_code": "BEBIDAS", "name": "Agua mineral 1.5L", "subtitle": "Garrafa grande", "description_short": "Opcao pratica para o dia inteiro.", "description": "Agua mineral natural em garrafa de 1.5L para consumo diario.", "price": "1.10", "sort_order": 10},
    {"code": "BEB_SUMO_LARANJA", "family_code": "BEBIDAS", "name": "Sumo de laranja 1L", "subtitle": "Pronto a beber", "description_short": "Ideal para pequeno-almoco ou lanche.", "description": "Sumo de laranja em embalagem de 1 litro, fresco e pratico.", "price": "2.30", "sort_order": 20},
    {"code": "BEB_REFRIG_COLA", "family_code": "BEBIDAS", "name": "Refrigerante cola 1.5L", "subtitle": "Formato familiar", "description_short": "Bom para acompanhar snacks e refeicoes.", "description": "Refrigerante de cola em garrafa grande, pensado para partilha.", "price": "2.60", "sort_order": 30},
    {"code": "BEB_CERVEJA_6X", "family_code": "BEBIDAS", "name": "Cerveja lager x6", "subtitle": "Pack com seis unidades", "description_short": "Rececao descontraida para dois ou mais.", "description": "Pack com seis garrafas de cerveja lager 33cl, fresco e simples.", "price": "5.50", "sort_order": 40},
    {"code": "BEB_VINHO_BRANCO", "family_code": "BEBIDAS", "name": "Vinho branco 75cl", "subtitle": "Selecao regional", "description_short": "Fresco e leve para aperitivo ou jantar.", "description": "Vinho branco portugues, versatil e facil para um primeiro brinde.", "price": "7.90", "sort_order": 50},
    {"code": "BEB_TONICA_4X", "family_code": "BEBIDAS", "name": "Agua tonica x4", "subtitle": "Pack tonica", "description_short": "Quatro garrafas pequenas para servir com gelo.", "description": "Conjunto de quatro garrafas de agua tonica, util como mixer ou bebida fresca.", "price": "3.40", "sort_order": 60},

    {"code": "HIG_GEL_BANHO", "family_code": "HIGIENE_PESSOAL", "name": "Gel de banho 250ml", "subtitle": "Fragrancia neutra", "description_short": "Conforto simples para estadias curtas.", "description": "Gel de banho suave, pensado para uso diario e utilizacao imediata.", "price": "3.20", "sort_order": 10},
    {"code": "HIG_CHAMPO_250", "family_code": "HIGIENE_PESSOAL", "name": "Champo 250ml", "subtitle": "Uso frequente", "description_short": "Essencial de higiene pessoal para bagagem leve.", "description": "Champo suave em formato standard para uso diario durante a estadia.", "price": "3.40", "sort_order": 20},
    {"code": "HIG_ESCOVA_PASTA", "family_code": "HIGIENE_PESSOAL", "name": "Escova e pasta de dentes", "subtitle": "Kit oral", "description_short": "Resolucao imediata para esquecimentos.", "description": "Kit de viagem com escova de dentes e pasta dentifrica em tamanho pratico.", "price": "2.95", "sort_order": 30},
    {"code": "HIG_GILETE_2X", "family_code": "HIGIENE_PESSOAL", "name": "Laminas descartaveis x2", "subtitle": "Pack com duas unidades", "description_short": "Pequeno essencial de conveniencia.", "description": "Conjunto com duas laminas descartaveis para pequenos imprevistos de viagem.", "price": "1.95", "sort_order": 40},
    {"code": "HIG_DESOD_150", "family_code": "HIGIENE_PESSOAL", "name": "Desodorizante spray 150ml", "subtitle": "Formato 150ml", "description_short": "Conforto e frescura para a estadia.", "description": "Desodorizante de uso diario em spray, pratico e compacto.", "price": "3.90", "sort_order": 50},
    {"code": "HIG_PENSOS_10", "family_code": "HIGIENE_PESSOAL", "name": "Pensos diarios x10", "subtitle": "Embalagem compacta", "description_short": "Item de conveniencia para necessidades imediatas.", "description": "Embalagem com dez pensos diarios, discreta e util para a chegada.", "price": "2.10", "sort_order": 60},

    {"code": "SUR_BALOES_SET", "family_code": "SURPRESAS", "name": "Kit baloes decorativos", "subtitle": "Conjunto pronto a montar", "description_short": "Pequena surpresa com impacto imediato.", "description": "Conjunto simples de baloes e fita para um gesto especial no alojamento.", "price": "4.90", "sort_order": 10},
    {"code": "SUR_VELAS_6", "family_code": "SURPRESAS", "name": "Velas aromaticas x6", "subtitle": "Aroma suave", "description_short": "Ajuda a criar um ambiente mais acolhedor.", "description": "Seis velas aromaticas para dar ambiente e conforto a chegada.", "price": "6.50", "sort_order": 20},
    {"code": "SUR_CHOCOLATE_BOX", "family_code": "SURPRESAS", "name": "Caixa mini chocolates", "subtitle": "Selecao premium", "description_short": "Mimo simples para partilhar ou oferecer.", "description": "Pequena caixa com chocolates variados, pensada para um gesto elegante.", "price": "5.80", "sort_order": 30},
    {"code": "SUR_FLORES_SECAS", "family_code": "SURPRESAS", "name": "Arranjo de flores secas", "subtitle": "Decoracao floral", "description_short": "Toque visual discreto e duradouro.", "description": "Pequeno arranjo decorativo de flores secas para acolher a estadia com mais cuidado.", "price": "9.50", "sort_order": 40},
    {"code": "SUR_CARTAO_WELCOME", "family_code": "SURPRESAS", "name": "Cartao welcome", "subtitle": "Mensagem curta", "description_short": "Detalhe simples para personalizar a chegada.", "description": "Cartao de boas-vindas com mensagem curta, perfeito para surpreender sem exagero.", "price": "1.50", "sort_order": 50},
    {"code": "SUR_PROSECCO_20", "family_code": "SURPRESAS", "name": "Espumante mini 20cl", "subtitle": "Garrafa individual", "description_short": "Pequeno brinde para um momento especial.", "description": "Mini espumante seco, ideal para celebrar discretamente a chegada.", "price": "4.70", "sort_order": 60},

    {"code": "UTI_GUARDA_CHUVA", "family_code": "UTILITARIOS", "name": "Guarda-chuva compacto", "subtitle": "Dobravel", "description_short": "Pratico para os dias de chuva no Porto.", "description": "Guarda-chuva leve e dobravel, util para imprevistos meteorologicos.", "price": "7.50", "sort_order": 10},
    {"code": "UTI_CARREGADOR_USB", "family_code": "UTILITARIOS", "name": "Carregador USB duplo", "subtitle": "Duas portas", "description_short": "Resolve esquecimentos frequentes de viagem.", "description": "Carregador de tomada com duas portas USB, ideal para telemoveis e pequenos dispositivos.", "price": "8.90", "sort_order": 20},
    {"code": "UTI_CABO_USB_C", "family_code": "UTILITARIOS", "name": "Cabo USB-C 1m", "subtitle": "Compativel USB-C", "description_short": "Acessorio util para smartphone e tablet.", "description": "Cabo USB-C de 1 metro para carregamento e dados, simples e eficaz.", "price": "4.90", "sort_order": 30},
    {"code": "UTI_PILHAS_AA_4", "family_code": "UTILITARIOS", "name": "Pilhas AA x4", "subtitle": "Pack com quatro unidades", "description_short": "Pequeno essencial para comandos e dispositivos.", "description": "Conjunto com quatro pilhas alcalinas AA para necessidades ocasionais.", "price": "3.60", "sort_order": 40},
    {"code": "UTI_SACO_LAVANDARIA", "family_code": "UTILITARIOS", "name": "Saco de lavandaria", "subtitle": "Reutilizavel", "description_short": "Ajuda a organizar roupa e bagagem.", "description": "Saco reutilizavel de tamanho medio para lavandaria ou organizacao da mala.", "price": "2.80", "sort_order": 50},
    {"code": "UTI_KIT_COSTURA", "family_code": "UTILITARIOS", "name": "Kit costura de viagem", "subtitle": "Compacto", "description_short": "Para pequenos imprevistos de roupa.", "description": "Mini kit com agulha, linha e botoes para reparacoes rapidas durante a estadia.", "price": "2.40", "sort_order": 60},

    {"code": "ADU_PRESERV_12", "family_code": "ADULT_MATERIAL", "name": "Preservativos x12", "subtitle": "Pack de 12 unidades", "description_short": "Artigo discreto de bem-estar adulto.", "description": "Caixa com doze preservativos, apresentada com descricao discreta e neutra.", "price": "8.90", "sort_order": 10},
    {"code": "ADU_LUBR_100", "family_code": "ADULT_MATERIAL", "name": "Lubrificante 100ml", "subtitle": "Base agua", "description_short": "Formato simples e discreto.", "description": "Lubrificante intimo de base aquosa em embalagem discreta para maior conveniencia.", "price": "9.50", "sort_order": 20},
    {"code": "ADU_MASSAGEM_100", "family_code": "ADULT_MATERIAL", "name": "Oleo de massagem 100ml", "subtitle": "Aroma neutro", "description_short": "Relaxamento e ambiente mais intimista.", "description": "Oleo corporal de massagem com aroma suave para uma experiencia mais tranquila.", "price": "11.90", "sort_order": 30},
    {"code": "ADU_VELA_MASSAGEM", "family_code": "ADULT_MATERIAL", "name": "Vela de massagem", "subtitle": "Ritual de relaxamento", "description_short": "Detalhe sensorial e discreto.", "description": "Vela de massagem com fragancia suave para criar ambiente e conforto.", "price": "12.90", "sort_order": 40},
    {"code": "ADU_KIT_BEM_ESTAR", "family_code": "ADULT_MATERIAL", "name": "Kit bem-estar adulto", "subtitle": "Essenciais selecionados", "description_short": "Conjunto discreto e pratico.", "description": "Kit com selecao de artigos de bem-estar adulto, pensado para maior conveniencia.", "price": "18.50", "sort_order": 50},
    {"code": "ADU_GEL_AQUEC_50", "family_code": "ADULT_MATERIAL", "name": "Gel aquecimento 50ml", "subtitle": "Formato compacto", "description_short": "Artigo discreto para bem-estar adulto.", "description": "Gel com efeito aquecimento em embalagem compacta e neutra.", "price": "10.90", "sort_order": 60},
]


def _to_price(value):
    return Decimal(str(value)).quantize(_DEC2, rounding=ROUND_HALF_UP)


def _table_exists(table_name):
    sql = text(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = :table_name
        """
    )
    return bool(db.session.execute(sql, {"table_name": table_name}).scalar() or 0)


def _public_image_url(raw_url):
    value = str(raw_url or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://", "/")):
        return value
    return f"/{value.lstrip('/')}"


def _display_variant_label(name, value):
    raw_name = str(name or "").strip()
    raw_value = str(value or "").strip()
    if raw_name and raw_value:
        normalized = raw_value.lower().replace(",", ".")
        if normalized in {"1", "1.0", "true"}:
            return raw_name
        if raw_value.lower() == raw_name.lower():
            return raw_name
        return f"{raw_name} · {raw_value}"
    return raw_name or raw_value


def _product_translations(name="", title="", subtitle="", description_short="", description="", row=None):
    row = row or {}
    return {
        "pt": {
            "name": str(name or "").strip(),
            "title": str(title or name or "").strip(),
            "subtitle": str(subtitle or "").strip(),
            "description_short": str(description_short or "").strip(),
            "description": str(description or "").strip(),
        },
        "en": {
            "name": str(row.get("NOME_EN") or "").strip(),
            "title": str(row.get("TITULO_EN") or "").strip(),
            "subtitle": str(row.get("SUBTITULO_EN") or "").strip(),
            "description_short": str(row.get("DESCRICAO_CURTA_EN") or "").strip(),
            "description": str(row.get("DESCRICAO_EN") or "").strip(),
        },
        "es": {
            "name": str(row.get("NOME_ES") or "").strip(),
            "title": str(row.get("TITULO_ES") or "").strip(),
            "subtitle": str(row.get("SUBTITULO_ES") or "").strip(),
            "description_short": str(row.get("DESCRICAO_CURTA_ES") or "").strip(),
            "description": str(row.get("DESCRICAO_ES") or "").strip(),
        },
        "fr": {
            "name": str(row.get("NOME_FR") or "").strip(),
            "title": str(row.get("TITULO_FR") or "").strip(),
            "subtitle": str(row.get("SUBTITULO_FR") or "").strip(),
            "description_short": str(row.get("DESCRICAO_CURTA_FR") or "").strip(),
            "description": str(row.get("DESCRICAO_FR") or "").strip(),
        },
    }


def _cart_line_key(product_code, variant_id=None):
    code = str(product_code or "").strip().upper()
    if not code:
        return ""
    try:
        variant_num = int(variant_id) if variant_id not in (None, "", 0, "0") else 0
    except Exception:
        variant_num = 0
    return f"{code}::{variant_num}" if variant_num > 0 else code


def _split_cart_line_key(raw_key):
    value = str(raw_key or "").strip().upper()
    if not value:
        return "", None
    if "::" not in value:
        return value, None
    product_code, variant_raw = value.split("::", 1)
    try:
        variant_id = int(variant_raw)
    except Exception:
        variant_id = None
    return product_code.strip().upper(), variant_id


def _db_catalog_available():
    return all(
        _table_exists(name)
        for name in ("SHOP_FAMILIAS", "SHOP_PRODUTOS", "SHOP_PRODUTO_IMAGENS")
    )


def _db_shop_catalog_data():
    rows = db.session.execute(
        text(
            """
            SELECT
                f.FAMILIA_ID,
                f.CODIGO AS FAMILIA_CODIGO,
                f.NOME AS FAMILIA_NOME,
                f.TITULO AS FAMILIA_TITULO,
                f.DESCRICAO AS FAMILIA_DESCRICAO,
                f.ORDEM AS FAMILIA_ORDEM,
                p.PRODUTO_ID,
                p.CODIGO AS PRODUTO_CODIGO,
                p.NOME AS PRODUTO_NOME,
                p.TITULO AS PRODUTO_TITULO,
                p.SUBTITULO AS PRODUTO_SUBTITULO,
                p.DESCRICAO_CURTA,
                p.DESCRICAO,
                p.NOME_EN,
                p.NOME_ES,
                p.NOME_FR,
                p.TITULO_EN,
                p.TITULO_ES,
                p.TITULO_FR,
                p.SUBTITULO_EN,
                p.SUBTITULO_ES,
                p.SUBTITULO_FR,
                p.DESCRICAO_CURTA_EN,
                p.DESCRICAO_CURTA_ES,
                p.DESCRICAO_CURTA_FR,
                p.DESCRICAO_EN,
                p.DESCRICAO_ES,
                p.DESCRICAO_FR,
                p.PRECO,
                p.MOEDA,
                p.ORDEM AS PRODUTO_ORDEM,
                (
                    SELECT TOP 1 pi.URL
                    FROM dbo.SHOP_PRODUTO_IMAGENS pi
                    WHERE pi.PRODUTO_ID = p.PRODUTO_ID
                      AND pi.ATIVO = 1
                    ORDER BY pi.E_PRINCIPAL DESC, pi.ORDEM ASC, pi.PRODUTO_IMAGEM_ID ASC
                ) AS IMAGEM_URL
            FROM dbo.SHOP_FAMILIAS f
            INNER JOIN dbo.SHOP_PRODUTOS p
                ON p.FAMILIA_ID = f.FAMILIA_ID
            WHERE f.ATIVO = 1
              AND p.ATIVO = 1
            ORDER BY f.ORDEM ASC, f.NOME ASC, p.ORDEM ASC, p.NOME ASC
            """
        )
    ).mappings().all()

    if not rows:
        return {"currency": "EUR", "families": [], "products": [], "products_by_family": {}, "source": "db"}

    product_ids = [int(row["PRODUTO_ID"]) for row in rows if row.get("PRODUTO_ID") is not None]
    variants_map = {}
    if product_ids and _table_exists("SHOP_PRODUTO_VARIANTES"):
        params = {f"pid{i}": pid for i, pid in enumerate(product_ids)}
        placeholders = ", ".join(f":pid{i}" for i in range(len(product_ids)))
        variant_rows = db.session.execute(
            text(
                f"""
                SELECT
                    PRODUTO_VARIANTE_ID, PRODUTO_ID, CODIGO, TIPO_VARIANTE, NOME, VALOR,
                    DESCRICAO_CURTA, PRECO, ORDEM, PADRAO, ATIVO
                FROM dbo.SHOP_PRODUTO_VARIANTES
                WHERE ATIVO = 1
                  AND PRODUTO_ID IN ({placeholders})
                ORDER BY PRODUTO_ID ASC, PADRAO DESC, ORDEM ASC, PRODUTO_VARIANTE_ID ASC
                """
            ),
            params,
        ).mappings().all()
        for variant_row in variant_rows:
            product_id = int(variant_row["PRODUTO_ID"])
            variants_map.setdefault(product_id, []).append(
                {
                    "id": int(variant_row["PRODUTO_VARIANTE_ID"]),
                    "code": str(variant_row.get("CODIGO") or "").strip().upper(),
                    "type": str(variant_row.get("TIPO_VARIANTE") or "").strip().upper(),
                    "name": str(variant_row.get("NOME") or "").strip(),
                    "value": str(variant_row.get("VALOR") or "").strip(),
                    "description_short": str(variant_row.get("DESCRICAO_CURTA") or "").strip(),
                    "price": float(_to_price(variant_row.get("PRECO"))) if variant_row.get("PRECO") is not None else None,
                    "sort_order": int(variant_row.get("ORDEM") or 0),
                    "is_default": bool(variant_row.get("PADRAO")),
                    "label": _display_variant_label(variant_row.get("NOME"), variant_row.get("VALOR")),
                }
            )

    families = []
    family_index = {}
    products = []

    for row in rows:
        family_code = str(row.get("FAMILIA_CODIGO") or "").strip().upper()
        if not family_code:
            continue
        if family_code not in family_index:
            ui_meta = _FAMILY_UI_META.get(family_code, {"icon": "fa-bag-shopping", "accent": "#2563eb"})
            family = {
                "id": row.get("FAMILIA_ID"),
                "code": family_code,
                "name": str(row.get("FAMILIA_NOME") or "").strip(),
                "title": str(row.get("FAMILIA_TITULO") or row.get("FAMILIA_NOME") or "").strip(),
                "description": str(row.get("FAMILIA_DESCRICAO") or "").strip(),
                "sort_order": int(row.get("FAMILIA_ORDEM") or 0),
                "icon": ui_meta["icon"],
                "accent": ui_meta["accent"],
                "products_count": 0,
            }
            family_index[family_code] = family
            families.append(family)

        family = family_index[family_code]
        price = _to_price(row.get("PRECO") or "0.00")
        product_variants = list(variants_map.get(int(row.get("PRODUTO_ID") or 0), []))
        default_variant = next((item for item in product_variants if item.get("is_default")), None) or (product_variants[0] if product_variants else None)
        product_name = str(row.get("PRODUTO_NOME") or "").strip()
        product_title = str(row.get("PRODUTO_TITULO") or row.get("PRODUTO_NOME") or "").strip()
        product_subtitle = str(row.get("PRODUTO_SUBTITULO") or "").strip()
        product_description_short = str(row.get("DESCRICAO_CURTA") or "").strip()
        product_description = str(row.get("DESCRICAO") or "").strip()
        products.append(
            {
                "id": row.get("PRODUTO_ID"),
                "code": str(row.get("PRODUTO_CODIGO") or "").strip().upper(),
                "family_code": family_code,
                "family_name": family["name"],
                "name": product_name,
                "title": product_title,
                "subtitle": product_subtitle,
                "description_short": product_description_short,
                "description": product_description,
                "translations": _product_translations(
                    product_name,
                    product_title,
                    product_subtitle,
                    product_description_short,
                    product_description,
                    row=row,
                ),
                "price": float(price),
                "currency": str(row.get("MOEDA") or "EUR").strip() or "EUR",
                "sort_order": int(row.get("PRODUTO_ORDEM") or 0),
                "icon": family["icon"],
                "accent": family["accent"],
                "image_url": _public_image_url(row.get("IMAGEM_URL")),
                "variants": product_variants,
                "has_variants": bool(product_variants),
                "default_variant_id": default_variant.get("id") if default_variant else None,
                "default_variant_label": default_variant.get("label") if default_variant else "",
            }
        )
        family["products_count"] += 1

    products_by_family = {}
    for family in families:
        products_by_family[family["code"]] = [item for item in products if item["family_code"] == family["code"]]

    return {
        "currency": "EUR",
        "families": families,
        "products": products,
        "products_by_family": products_by_family,
        "source": "db",
    }


def _fallback_shop_catalog_data():
    families = [dict(item) for item in sorted(_SHOP_FAMILIES, key=lambda item: (item["sort_order"], item["name"]))]
    family_index = {item["code"]: item for item in families}
    products = []
    for item in sorted(_SHOP_PRODUCTS, key=lambda row: (family_index[row["family_code"]]["sort_order"], row["sort_order"], row["name"])):
        family = family_index[item["family_code"]]
        price = _to_price(item["price"])
        product = {
            "code": item["code"],
            "family_code": item["family_code"],
            "family_name": family["name"],
            "name": item["name"],
            "title": item["name"],
            "subtitle": item["subtitle"],
            "description_short": item["description_short"],
            "description": item["description"],
            "translations": _product_translations(
                item["name"],
                item["name"],
                item["subtitle"],
                item["description_short"],
                item["description"],
            ),
            "price": float(price),
            "currency": "EUR",
            "sort_order": item["sort_order"],
            "icon": family["icon"],
            "accent": family["accent"],
            "image_url": "",
            "variants": [],
            "has_variants": False,
            "default_variant_id": None,
            "default_variant_label": "",
        }
        products.append(product)

    products_by_family = {}
    for family in families:
        family_products = [item for item in products if item["family_code"] == family["code"]]
        products_by_family[family["code"]] = family_products
        family["products_count"] = len(family_products)

    return {
        "currency": "EUR",
        "families": families,
        "products": products,
        "products_by_family": products_by_family,
        "source": "fallback",
    }


def get_shop_catalog_data():
    try:
        if _db_catalog_available():
            return _db_shop_catalog_data()
    except Exception:
        pass
    return _fallback_shop_catalog_data()


def get_shop_product_by_code(product_code):
    code = str(product_code or "").strip().upper()
    if not code:
        return None
    catalog = get_shop_catalog_data()
    for product in catalog["products"]:
        if product["code"] == code:
            return dict(product)
    return None


def build_shop_cart(raw_lines):
    catalog = get_shop_catalog_data()
    product_index = {item["code"]: item for item in catalog["products"]}
    items = []
    total_quantity = 0
    subtotal = Decimal("0.00")

    for raw_key, qty in (raw_lines or {}).items():
        code, variant_id = _split_cart_line_key(raw_key)
        if not code or code not in product_index:
            continue
        try:
            quantity = int(qty)
        except Exception:
            quantity = 0
        if quantity <= 0:
            continue
        product = product_index[code]
        variant = None
        if variant_id:
            variant = next((item for item in (product.get("variants") or []) if int(item.get("id") or 0) == int(variant_id)), None)
        unit_price = _to_price(variant["price"] if variant and variant.get("price") is not None else product["price"])
        line_total = (unit_price * quantity).quantize(_DEC2, rounding=ROUND_HALF_UP)
        items.append(
            {
                "key": _cart_line_key(code, variant_id),
                "product_code": code,
                "product_name": product["name"],
                "subtitle": product["subtitle"],
                "translations": product.get("translations") or {},
                "variant_id": variant.get("id") if variant else None,
                "variant_label": variant.get("label") if variant else "",
                "family_code": product["family_code"],
                "family_name": product["family_name"],
                "quantity": quantity,
                "unit_price": float(unit_price),
                "line_total": float(line_total),
                "currency": product["currency"],
                "icon": product["icon"],
                "accent": product["accent"],
                "image_url": product.get("image_url") or "",
            }
        )
        total_quantity += quantity
        subtotal += line_total

    items.sort(key=lambda item: (item["family_name"], item["product_name"], item.get("variant_label") or ""))
    subtotal = subtotal.quantize(_DEC2, rounding=ROUND_HALF_UP)
    return {
        "currency": "EUR",
        "items": items,
        "items_count": len(items),
        "total_quantity": total_quantity,
        "subtotal": float(subtotal),
        "total": float(subtotal),
    }
