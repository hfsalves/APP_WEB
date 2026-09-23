"""StationZero accommodation amenities catalogue and N:N assignments."""

from __future__ import annotations

import re
import uuid

from flask import current_app
from sqlalchemy import bindparam, text

from models import db


CATEGORIES = (
    "CLIMATIZACAO", "COZINHA", "LAVANDARIA", "QUARTO_BANHO",
    "TECNOLOGIA", "EXTERIOR", "EDIFICIO_ACESSO", "BEBE", "OUTROS",
)

CATEGORY_LABELS = {
    "CLIMATIZACAO": "Climatização",
    "COZINHA": "Cozinha",
    "LAVANDARIA": "Lavandaria",
    "QUARTO_BANHO": "Quarto / Casa de banho",
    "TECNOLOGIA": "Tecnologia",
    "EXTERIOR": "Exterior",
    "EDIFICIO_ACESSO": "Edifício / Acesso",
    "BEBE": "Bebé",
    "OUTROS": "Outros",
}

ICON_OPTIONS = (
    "fa-snowflake", "fa-temperature-half", "fa-fan", "fa-kitchen-set",
    "fa-utensils", "fa-box", "fa-icicles", "fa-fire-burner", "fa-fire",
    "fa-wave-square", "fa-mug-hot", "fa-mug-saucer", "fa-bread-slice",
    "fa-sink", "fa-shirt", "fa-person-booth", "fa-soap", "fa-pump-soap",
    "fa-bottle-droplet", "fa-bed",
    "fa-bath", "fa-shower", "fa-sun", "fa-wifi", "fa-tv", "fa-display",
    "fa-satellite-dish", "fa-building", "fa-umbrella-beach", "fa-tree",
    "fa-chair", "fa-elevator", "fa-square-parking", "fa-car", "fa-house",
    "fa-baby", "fa-baby-carriage", "fa-briefcase", "fa-couch", "fa-vault",
)

# Code, PT, EN, ES, FR, category, icon, order, show, filter.
INITIAL_AMENITIES = (
    ("AR_CONDICIONADO", "Ar condicionado", "Air conditioning", "Aire acondicionado", "Climatisation", "CLIMATIZACAO", "fa-snowflake", 10, 1, 1),
    ("AQUECIMENTO", "Aquecimento", "Heating", "Calefacción", "Chauffage", "CLIMATIZACAO", "fa-temperature-half", 20, 1, 1),
    ("VENTOINHA", "Ventoinha", "Fan", "Ventilador", "Ventilateur", "CLIMATIZACAO", "fa-fan", 30, 1, 0),
    ("COZINHA", "Cozinha", "Kitchen", "Cocina", "Cuisine", "COZINHA", "fa-kitchen-set", 10, 1, 1),
    ("KITCHENETTE", "Kitchenette", "Kitchenette", "Cocina americana", "Kitchenette", "COZINHA", "fa-utensils", 20, 1, 0),
    ("FRIGORIFICO", "Frigorífico", "Refrigerator", "Frigorífico", "Réfrigérateur", "COZINHA", "fa-box", 30, 1, 0),
    ("CONGELADOR", "Congelador", "Freezer", "Congelador", "Congélateur", "COZINHA", "fa-icicles", 40, 1, 0),
    ("PLACA", "Placa", "Stovetop", "Placa de cocina", "Plaque de cuisson", "COZINHA", "fa-fire-burner", 50, 1, 0),
    ("FORNO", "Forno", "Oven", "Horno", "Four", "COZINHA", "fa-fire", 60, 1, 0),
    ("MICRO_ONDAS", "Micro-ondas", "Microwave", "Microondas", "Micro-ondes", "COZINHA", "fa-wave-square", 70, 1, 0),
    ("MAQUINA_CAFE", "Máquina de café", "Coffee maker", "Cafetera", "Machine à café", "COZINHA", "fa-mug-hot", 80, 1, 0),
    ("CHALEIRA_ELETRICA", "Chaleira elétrica", "Electric kettle", "Hervidor eléctrico", "Bouilloire électrique", "COZINHA", "fa-mug-saucer", 90, 1, 0),
    ("TORRADEIRA", "Torradeira", "Toaster", "Tostadora", "Grille-pain", "COZINHA", "fa-bread-slice", 100, 1, 0),
    ("MAQUINA_LAVAR_LOICA", "Máquina de lavar loiça", "Dishwasher", "Lavavajillas", "Lave-vaisselle", "COZINHA", "fa-sink", 110, 1, 1),
    ("MAQUINA_LAVAR_ROUPA", "Máquina de lavar roupa", "Washing machine", "Lavadora", "Lave-linge", "LAVANDARIA", "fa-shirt", 10, 1, 1),
    ("ESTENDAL", "Estendal", "Drying rack", "Tendedero", "Étendoir à linge", "LAVANDARIA", "fa-person-booth", 20, 1, 0),
    ("FERRO_ENGOMAR", "Ferro de engomar", "Iron", "Plancha", "Fer à repasser", "LAVANDARIA", "fa-shirt", 30, 1, 0),
    ("TABUA_ENGOMAR", "Tábua de engomar", "Ironing board", "Tabla de planchar", "Planche à repasser", "LAVANDARIA", "fa-person-booth", 40, 1, 0),
    ("ROUPA_CAMA", "Roupa de cama", "Bed linen", "Ropa de cama", "Linge de lit", "QUARTO_BANHO", "fa-bed", 10, 1, 0),
    ("TOALHAS", "Toalhas", "Towels", "Toallas", "Serviettes", "QUARTO_BANHO", "fa-soap", 20, 1, 0),
    ("SECADOR_CABELO", "Secador de cabelo", "Hair dryer", "Secador de pelo", "Sèche-cheveux", "QUARTO_BANHO", "fa-fan", 30, 1, 0),
    ("BANHEIRA", "Banheira", "Bathtub", "Bañera", "Baignoire", "QUARTO_BANHO", "fa-bath", 40, 1, 1),
    ("DUCHE", "Duche", "Shower", "Ducha", "Douche", "QUARTO_BANHO", "fa-shower", 50, 1, 0),
    ("BLACKOUT", "Blackout / estores opacos", "Blackout blinds", "Persianas opacas", "Stores occultants", "QUARTO_BANHO", "fa-sun", 60, 1, 0),
    ("GEL_DUCHE", "Gel de duche", "Shower gel", "Gel de ducha", "Gel douche", "QUARTO_BANHO", "fa-pump-soap", 70, 1, 0),
    ("SHAMPOO", "Shampoo", "Shampoo", "Champú", "Shampoing", "QUARTO_BANHO", "fa-bottle-droplet", 80, 1, 0),
    ("SABONETE_LIQUIDO", "Sabonete líquido", "Liquid soap", "Jabón líquido", "Savon liquide", "QUARTO_BANHO", "fa-pump-soap", 90, 1, 0),
    ("WIFI", "Wi-Fi", "Wi-Fi", "Wi-Fi", "Wi-Fi", "TECNOLOGIA", "fa-wifi", 10, 1, 1),
    ("TELEVISAO", "Televisão", "Television", "Televisión", "Télévision", "TECNOLOGIA", "fa-tv", 20, 1, 0),
    ("SMART_TV", "Smart TV", "Smart TV", "Smart TV", "Smart TV", "TECNOLOGIA", "fa-display", 30, 1, 1),
    ("TV_CABO", "TV por cabo", "Cable TV", "Televisión por cable", "Télévision par câble", "TECNOLOGIA", "fa-satellite-dish", 40, 1, 0),
    ("VARANDA", "Varanda", "Balcony", "Balcón", "Balcon", "EXTERIOR", "fa-building", 10, 1, 1),
    ("TERRACO", "Terraço", "Terrace", "Terraza", "Terrasse", "EXTERIOR", "fa-umbrella-beach", 20, 1, 1),
    ("JARDIM_PATIO", "Jardim / Pátio", "Garden / Patio", "Jardín / Patio", "Jardin / Patio", "EXTERIOR", "fa-tree", 30, 1, 1),
    ("MOBILIARIO_EXTERIOR", "Mobiliário exterior", "Outdoor furniture", "Muebles de exterior", "Mobilier d’extérieur", "EXTERIOR", "fa-chair", 40, 1, 0),
    ("ELEVADOR", "Elevador", "Lift", "Ascensor", "Ascenseur", "EDIFICIO_ACESSO", "fa-elevator", 10, 1, 1),
    ("ESTACIONAMENTO_PRIVADO", "Estacionamento privado", "Private parking", "Aparcamiento privado", "Parking privé", "EDIFICIO_ACESSO", "fa-square-parking", 20, 1, 1),
    ("ESTACIONAMENTO_GRATUITO", "Estacionamento gratuito", "Free parking", "Aparcamiento gratuito", "Parking gratuit", "EDIFICIO_ACESSO", "fa-car", 30, 1, 1),
    ("RES_DO_CHAO", "Rés-do-chão", "Ground floor", "Planta baja", "Rez-de-chaussée", "EDIFICIO_ACESSO", "fa-house", 40, 1, 1),
    ("BERCO", "Berço", "Cot", "Cuna", "Lit bébé", "BEBE", "fa-baby", 10, 1, 1),
    ("CADEIRA_BEBE", "Cadeira de bebé", "High chair", "Trona", "Chaise haute", "BEBE", "fa-baby-carriage", 20, 1, 0),
    ("ESPACO_TRABALHO", "Espaço de trabalho / secretária", "Dedicated workspace / desk", "Zona de trabajo / escritorio", "Espace de travail / bureau", "OUTROS", "fa-briefcase", 10, 1, 1),
    ("SOFA_CAMA", "Sofá-cama", "Sofa bed", "Sofá cama", "Canapé-lit", "OUTROS", "fa-couch", 20, 1, 1),
    ("COFRE", "Cofre", "Safe", "Caja fuerte", "Coffre-fort", "OUTROS", "fa-vault", 30, 1, 0),
)

MENU_STAMP = "ALCOMODIDADESMENU00000001"


def normalize_code(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^A-Z0-9_]", "_", str(value or "").strip().upper())).strip("_")


def _boolean(value, label: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise ValueError(f"O campo {label} deve ser booleano.")


def normalize_amenity_payload(payload: dict, *, creating: bool) -> dict:
    code = normalize_code(payload.get("codigo"))
    names = {key: str(payload.get(key) or "").strip() for key in ("nome_pt", "nome_en", "nome_es", "nome_fr")}
    category = str(payload.get("categoria") or "").strip().upper()
    icon = str(payload.get("icone") or "").strip()
    try:
        order = int(payload.get("ordem") or 0)
    except (TypeError, ValueError):
        raise ValueError("A ordem deve ser um número inteiro.")
    if creating and not code:
        raise ValueError("O código é obrigatório.")
    if code and (len(code) > 60 or not re.fullmatch(r"[A-Z0-9_]+", code)):
        raise ValueError("O código só pode conter letras, números e underscores.")
    if any(not value for value in names.values()):
        raise ValueError("As quatro designações são obrigatórias.")
    if any(len(value) > 120 for value in names.values()):
        raise ValueError("As designações não podem exceder 120 caracteres.")
    if category not in CATEGORIES:
        raise ValueError("A categoria selecionada não é válida.")
    if icon not in ICON_OPTIONS:
        raise ValueError("O ícone selecionado não é válido.")
    active = _boolean(payload.get("ativa"), "Ativa")
    show = _boolean(payload.get("mostra_portobreak"), "Mostrar no PortoBreak")
    filtering = _boolean(payload.get("filtro_portobreak"), "Filtro PortoBreak")
    if filtering:
        active = True
        show = True
    if not active or not show:
        filtering = False
    return {
        "codigo": code, **names, "categoria": category, "icone": icon, "ordem": order,
        "ativa": active, "mostra_portobreak": show, "filtro_portobreak": filtering,
    }


def ensure_amenities_schema() -> None:
    if db.engine.dialect.name != "mssql":
        return
    migration = current_app.root_path + "/migrations/al_comodidades.sql"
    with open(migration, "r", encoding="utf-8") as handle:
        batches = [part.strip() for part in re.split(r"^\s*GO\s*$", handle.read(), flags=re.MULTILINE | re.IGNORECASE) if part.strip()]
    for batch in batches:
        db.session.execute(text(batch))
    # A carga é apenas inicial. Se voltássemos a inserir por código em todos os
    # arranques, uma comodidade eliminada pelo utilizador reapareceria.
    if not db.session.execute(text("SELECT TOP 1 1 FROM dbo.COMODIDADES")).scalar():
        for item in INITIAL_AMENITIES:
            db.session.execute(text("""
                INSERT INTO dbo.COMODIDADES
                    (CODIGO,NOME_PT,NOME_EN,NOME_ES,NOME_FR,CATEGORIA,ICONE,ORDEM,ATIVA,MOSTRA_PORTOBREAK,FILTRO_PORTOBREAK)
                VALUES
                    (:codigo,:pt,:en,:es,:fr,:categoria,:icone,:ordem,1,:mostra,:filtro)
            """), dict(zip(("codigo", "pt", "en", "es", "fr", "categoria", "icone", "ordem", "mostra", "filtro"), item)))
    # Corrige apenas os dois identificadores iniciais que não existem no
    # Font Awesome Free 6.4; não substitui escolhas posteriores do utilizador.
    db.session.execute(text("""
        UPDATE dbo.COMODIDADES SET ICONE='fa-wave-square'
        WHERE CODIGO='MICRO_ONDAS' AND ICONE='fa-microwave';
        UPDATE dbo.COMODIDADES SET ICONE='fa-mug-saucer'
        WHERE CODIGO='CHALEIRA_ELETRICA' AND ICONE='fa-kettle';
    """))
    menu_exists = db.session.execute(text("SELECT 1 FROM dbo.MENU WHERE MENUSTAMP=:stamp OR URL='/alojamentos/comodidades'"), {"stamp": MENU_STAMP}).scalar()
    if not menu_exists:
        db.session.execute(text("""
            INSERT INTO dbo.MENU (MENUSTAMP,ORDEM,NOME,TABELA,URL,ADMIN,ICONE,FORM,ORDERBY,NOVO,INATIVO)
            VALUES (:stamp,202,'Comodidades dos Alojamentos','AL','/alojamentos/comodidades',0,'fa-solid fa-list-check','','',0,0)
        """), {"stamp": MENU_STAMP})
    db.session.commit()


def list_amenities(*, include_inactive: bool = True) -> list[dict]:
    where = "" if include_inactive else "WHERE ATIVA=1"
    rows = db.session.execute(text(f"""
        SELECT ID,CODIGO,NOME_PT,NOME_EN,NOME_ES,NOME_FR,CATEGORIA,ICONE,ORDEM,
               CAST(ATIVA AS int) ATIVA,CAST(MOSTRA_PORTOBREAK AS int) MOSTRA_PORTOBREAK,
               CAST(FILTRO_PORTOBREAK AS int) FILTRO_PORTOBREAK,
               (SELECT COUNT(*) FROM dbo.AL_COMODIDADES AC WHERE AC.COMODIDADE_ID=COMODIDADES.ID) ASSOCIACOES
        FROM dbo.COMODIDADES {where}
        ORDER BY CASE CATEGORIA
          WHEN 'CLIMATIZACAO' THEN 1 WHEN 'COZINHA' THEN 2 WHEN 'LAVANDARIA' THEN 3
          WHEN 'QUARTO_BANHO' THEN 4 WHEN 'TECNOLOGIA' THEN 5 WHEN 'EXTERIOR' THEN 6
          WHEN 'EDIFICIO_ACESSO' THEN 7 WHEN 'BEBE' THEN 8 ELSE 9 END, ORDEM, NOME_PT
    """)).mappings().all()
    return [{str(k).lower(): v for k, v in dict(row).items()} for row in rows]


def _property_scope_sql(alias: str = "AL") -> str:
    return f"(ISNULL({alias}.FEID,0)=:feid OR ISNULL({alias}.FEID_GESTOR,0)=:feid)"


def list_matrix(feid: int, *, query: str = "", zone: str = "") -> dict:
    clauses = ["ISNULL(AL.INATIVO,0)=0", _property_scope_sql()]
    params = {"feid": int(feid)}
    if query.strip():
        clauses.append("AL.NOME LIKE :query")
        params["query"] = f"%{query.strip()}%"
    if zone.strip():
        clauses.append("LTRIM(RTRIM(ISNULL(AL.ZONA,'')))=:zone")
        params["zone"] = zone.strip()
    properties = [dict(row) for row in db.session.execute(text(f"""
        SELECT AL.ALSTAMP,AL.NOME,ISNULL(AL.ZONA,'') ZONA,ISNULL(AL.LOCAL,'') LOCAL
        FROM dbo.AL AL WHERE {' AND '.join(clauses)} ORDER BY AL.NOME
    """), params).mappings().all()]
    names = [row["NOME"] for row in properties]
    relations: list[dict] = []
    if names:
        stmt = text("SELECT ALOJAMENTO,COMODIDADE_ID FROM dbo.AL_COMODIDADES WHERE ALOJAMENTO IN :names").bindparams(bindparam("names", expanding=True))
        relations = [dict(row) for row in db.session.execute(stmt, {"names": names}).mappings().all()]
    zones = [str(value or "").strip() for value in db.session.execute(text(f"""
        SELECT DISTINCT ISNULL(AL.ZONA,'') FROM dbo.AL AL
        WHERE ISNULL(AL.INATIVO,0)=0 AND {_property_scope_sql()} AND LTRIM(RTRIM(ISNULL(AL.ZONA,'')))<>''
        ORDER BY 1
    """), {"feid": int(feid)}).scalars().all()]
    return {"properties": properties, "relations": relations, "zones": zones}


def property_in_scope(alojamento: str, feid: int) -> bool:
    return bool(db.session.execute(text(f"SELECT 1 FROM dbo.AL AL WHERE AL.NOME=:nome AND ISNULL(AL.INATIVO,0)=0 AND {_property_scope_sql()}"), {"nome": alojamento, "feid": int(feid)}).scalar())


def amenity_exists(amenity_id: int, *, active_only: bool = False) -> bool:
    extra = " AND ATIVA=1" if active_only else ""
    return bool(db.session.execute(text(f"SELECT 1 FROM dbo.COMODIDADES WHERE ID=:id{extra}"), {"id": int(amenity_id)}).scalar())


def set_relation(alojamento: str, amenity_id: int, enabled: bool) -> None:
    if enabled:
        db.session.execute(text("""
            IF NOT EXISTS (SELECT 1 FROM dbo.AL_COMODIDADES WHERE ALOJAMENTO=:nome AND COMODIDADE_ID=:id)
            INSERT INTO dbo.AL_COMODIDADES (ALOJAMENTO,COMODIDADE_ID) VALUES (:nome,:id)
        """), {"nome": alojamento, "id": int(amenity_id)})
    else:
        db.session.execute(text("DELETE FROM dbo.AL_COMODIDADES WHERE ALOJAMENTO=:nome AND COMODIDADE_ID=:id"), {"nome": alojamento, "id": int(amenity_id)})


def create_amenity(payload: dict) -> dict:
    clean = normalize_amenity_payload(payload, creating=True)
    if db.session.execute(text("SELECT 1 FROM dbo.COMODIDADES WHERE CODIGO=:codigo"), clean).scalar():
        raise ValueError("Já existe uma comodidade com este código.")
    row = db.session.execute(text("""
        INSERT INTO dbo.COMODIDADES
          (CODIGO,NOME_PT,NOME_EN,NOME_ES,NOME_FR,CATEGORIA,ICONE,ORDEM,ATIVA,MOSTRA_PORTOBREAK,FILTRO_PORTOBREAK)
        OUTPUT INSERTED.ID
        VALUES (:codigo,:nome_pt,:nome_en,:nome_es,:nome_fr,:categoria,:icone,:ordem,:ativa,:mostra_portobreak,:filtro_portobreak)
    """), clean).scalar_one()
    db.session.commit()
    return next(item for item in list_amenities() if int(item["id"]) == int(row))


def update_amenity(amenity_id: int, payload: dict) -> dict:
    clean = normalize_amenity_payload(payload, creating=False)
    if not amenity_exists(amenity_id):
        raise LookupError("Comodidade não encontrada.")
    clean["id"] = int(amenity_id)
    db.session.execute(text("""
        UPDATE dbo.COMODIDADES SET NOME_PT=:nome_pt,NOME_EN=:nome_en,NOME_ES=:nome_es,NOME_FR=:nome_fr,
          CATEGORIA=:categoria,ICONE=:icone,ORDEM=:ordem,ATIVA=:ativa,
          MOSTRA_PORTOBREAK=:mostra_portobreak,FILTRO_PORTOBREAK=:filtro_portobreak
        WHERE ID=:id
    """), clean)
    db.session.commit()
    return next(item for item in list_amenities() if int(item["id"]) == int(amenity_id))


def delete_amenity(amenity_id: int) -> dict:
    row = db.session.execute(text(
        "SELECT ID,NOME_PT FROM dbo.COMODIDADES WHERE ID=:id"
    ), {"id": int(amenity_id)}).mappings().first()
    if not row:
        raise LookupError("Comodidade não encontrada.")
    relations = int(db.session.execute(text(
        "SELECT COUNT(*) FROM dbo.AL_COMODIDADES WHERE COMODIDADE_ID=:id"
    ), {"id": int(amenity_id)}).scalar() or 0)
    db.session.execute(text(
        "DELETE FROM dbo.AL_COMODIDADES WHERE COMODIDADE_ID=:id"
    ), {"id": int(amenity_id)})
    db.session.execute(text(
        "DELETE FROM dbo.COMODIDADES WHERE ID=:id"
    ), {"id": int(amenity_id)})
    db.session.commit()
    return {"id": int(row["ID"]), "nome_pt": row["NOME_PT"], "associacoes_removidas": relations}


def bulk_set_relations(alojamentos: list[str], amenity_id: int, enabled: bool, feid: int) -> int:
    unique = list(dict.fromkeys(str(value or "").strip() for value in alojamentos if str(value or "").strip()))
    if not unique:
        return 0
    stmt = text(f"SELECT AL.NOME FROM dbo.AL AL WHERE AL.NOME IN :names AND ISNULL(AL.INATIVO,0)=0 AND {_property_scope_sql()}").bindparams(bindparam("names", expanding=True))
    allowed = set(db.session.execute(stmt, {"names": unique, "feid": int(feid)}).scalars().all())
    if len(allowed) != len(unique):
        raise PermissionError("Existem alojamentos fora do âmbito da entidade ativa.")
    for nome in unique:
        set_relation(nome, amenity_id, enabled)
    db.session.commit()
    return len(unique)
