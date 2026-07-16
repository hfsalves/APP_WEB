#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Um script sem request nao tem hostname para selecionar a base client.
os.environ["APP_DB_TARGET"] = "client"

from app import app
from services.phc_va_attachments_service import sync_phc_va_attachments


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sincroniza metadados de anexos PHC das viaturas com a GR360_CORE."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Insere/atualiza os registos. Sem esta flag faz apenas a analise.",
    )
    args = parser.parse_args()

    with app.app_context():
        result = sync_phc_va_attachments(execute=args.execute)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
