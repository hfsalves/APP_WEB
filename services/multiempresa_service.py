import logging
from typing import Any, Dict, List

from flask import session
from sqlalchemy import text

from services.auth_service import get_table_columns


logger = logging.getLogger("stationzero.multiempresa")


class MissingUserEntitiesError(Exception):
    pass


class MissingCurrentEntityError(Exception):
    pass


def get_user_entities(db_session, usstamp: str) -> List[Dict[str, Any]]:
    usstamp = (usstamp or "").strip()
    if not usstamp:
        return []

    fe_columns = get_table_columns(db_session, "FE")
    fe_active_filter = "AND ISNULL(FE.ATIVA, 0) = 1" if "ATIVA" in fe_columns else ""

    rows = db_session.execute(
        text(
            f"""
            SELECT
                FE.FEID,
                ISNULL(FE.NOME, '') AS NOME,
                ISNULL(UF.PRINCIPAL, 0) AS PRINCIPAL,
                ISNULL(UF.ATIVO, 0) AS ATIVO
            FROM dbo.US_FE UF
            INNER JOIN dbo.FE FE
                ON FE.FEID = UF.FEID
            WHERE
                UF.USSTAMP = :usstamp
                AND ISNULL(UF.ATIVO, 0) = 1
                {fe_active_filter}
            ORDER BY
                ISNULL(UF.PRINCIPAL, 0) DESC,
                FE.FEID ASC,
                ISNULL(FE.NOME, '')
            """
        ),
        {"usstamp": usstamp},
    ).mappings().all()

    entities = [
        {
            "FEID": row.get("FEID"),
            "NOME": (row.get("NOME") or "").strip(),
            "PRINCIPAL": bool(row.get("PRINCIPAL") or 0),
            "ATIVO": bool(row.get("ATIVO") or 0),
        }
        for row in rows
    ]
    logger.info(
        "Entidades do utilizador carregadas",
        extra={"usstamp": usstamp, "entity_count": len(entities)},
    )
    return entities


def get_default_entity_for_user(db_session, usstamp: str) -> Dict[str, Any]:
    entities = get_user_entities(db_session, usstamp)
    if not entities:
        logger.warning("Utilizador sem entidades ativas", extra={"usstamp": usstamp})
        raise MissingUserEntitiesError("Sem entidades ativas associadas ao utilizador.")

    if len(entities) == 1:
        chosen = entities[0]
    else:
        principal = next((entity for entity in entities if entity.get("PRINCIPAL")), None)
        chosen = principal or entities[0]

    logger.info(
        "Entidade ativa por defeito selecionada",
        extra={"usstamp": usstamp, "feid": chosen.get("FEID"), "principal": bool(chosen.get("PRINCIPAL"))},
    )
    return chosen


def store_current_entity_in_session(entity: Dict[str, Any]) -> None:
    session["current_feid"] = entity.get("FEID")
    session["current_entity_name"] = entity.get("NOME") or ""


def get_current_feid() -> int:
    feid = session.get("current_feid")
    if feid in (None, ""):
        raise MissingCurrentEntityError("Empresa ativa não definida na sessão.")
    return int(feid)


def get_current_entity_context() -> Dict[str, Any]:
    feid = session.get("current_feid")
    if feid in (None, ""):
        raise MissingCurrentEntityError("Empresa ativa não definida na sessão.")
    return {
        "FEID": int(feid),
        "NOME": (session.get("current_entity_name") or "").strip(),
    }
