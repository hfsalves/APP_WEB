from decimal import Decimal, ROUND_HALF_UP


_DEC2 = Decimal("0.01")


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


def get_shop_catalog_data():
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
            "price": float(price),
            "currency": "EUR",
            "sort_order": item["sort_order"],
            "icon": family["icon"],
            "accent": family["accent"],
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
    }


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

    for product_code, qty in (raw_lines or {}).items():
        code = str(product_code or "").strip().upper()
        if not code or code not in product_index:
            continue
        try:
            quantity = int(qty)
        except Exception:
            quantity = 0
        if quantity <= 0:
            continue
        product = product_index[code]
        unit_price = _to_price(product["price"])
        line_total = (unit_price * quantity).quantize(_DEC2, rounding=ROUND_HALF_UP)
        items.append(
            {
                "product_code": code,
                "product_name": product["name"],
                "subtitle": product["subtitle"],
                "family_code": product["family_code"],
                "family_name": product["family_name"],
                "quantity": quantity,
                "unit_price": float(unit_price),
                "line_total": float(line_total),
                "currency": product["currency"],
                "icon": product["icon"],
                "accent": product["accent"],
            }
        )
        total_quantity += quantity
        subtotal += line_total

    items.sort(key=lambda item: (item["family_name"], item["product_name"]))
    subtotal = subtotal.quantize(_DEC2, rounding=ROUND_HALF_UP)
    return {
        "currency": "EUR",
        "items": items,
        "items_count": len(items),
        "total_quantity": total_quantity,
        "subtotal": float(subtotal),
        "total": float(subtotal),
    }
