import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
from sqlalchemy import text
from models import db  # ou de onde importas db

bp = Blueprint('anexos', __name__, url_prefix='/api/anexos')

# Pasta onde vamos guardar os ficheiros (relativa a current_app.root_path)
UPLOAD_FOLDER = os.path.join('static', 'images', 'anexos')
ALLOWED_EXT = {'png','jpg','jpeg','gif','pdf','docx','xlsx','txt','webm','mp4','mov','m4v'}

# — Listar anexos de um registo —
@bp.route('', methods=['GET'])
@login_required
def list_anexos():
    tabela   = (request.args.get('table', '') or '').strip()
    recstamp = (request.args.get('rec', '') or '').strip()
    # Tornar a pesquisa robusta a espaos e maisculas, e permitir anexos antigos sem TABELA preenchida
    sql = text("""
        SELECT ANEXOSSTAMP, TABELA, RECSTAMP, DESCRICAO, FICHEIRO, CAMINHO, TIPO, DATA, UTILIZADOR
          FROM ANEXOS
         WHERE (
                 (UPPER(LTRIM(RTRIM(TABELA))) = UPPER(:t) AND LTRIM(RTRIM(RECSTAMP)) = :r)
              OR (:t = '' AND LTRIM(RTRIM(RECSTAMP)) = :r)
              OR (UPPER(:t) = 'MN' AND (TABELA IS NULL OR LTRIM(RTRIM(TABELA)) = '') AND LTRIM(RTRIM(RECSTAMP)) = :r)
              )
         ORDER BY DATA DESC
    """)
    rows = db.session.execute(sql, {'t': tabela, 'r': recstamp}).mappings().all()
    return jsonify([dict(r) for r in rows])

# — Fazer upload de um novo anexo —
@bp.route('/upload', methods=['POST'])
@login_required
def upload_anexo():
    # Campos obrigatórios
    f      = request.files.get('file')
    tabela = request.form.get('table', '')
    rec    = request.form.get('rec', '')
    desc   = request.form.get('descricao', '')
    user   = getattr(request, 'remote_user', '') or ''  # ou current_user.LOGIN

    if not f or not tabela or not rec:
        return jsonify({'error': 'table, rec e file são obrigatórios'}), 400

    # Valida extensão
    filename = secure_filename(f.filename)
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({'error': f'Extensão .{ext} não suportada'}), 400

    # Gera nome único e caminho
    stamp = uuid.uuid4().hex[:25]
    new_fname = f"{stamp}.{ext}"
    save_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
    os.makedirs(save_dir, exist_ok=True)
    full_path = os.path.join(save_dir, new_fname)
    f.save(full_path)

    # Caminho público para servir o ficheiro
    public_path = f"/{UPLOAD_FOLDER}/{new_fname}"

    # Insere na BD
    sql_ins = text("""
      INSERT INTO ANEXOS
        (ANEXOSSTAMP, TABELA, RECSTAMP, DESCRICAO, FICHEIRO, CAMINHO, TIPO, DATA, UTILIZADOR)
      VALUES
        (:stamp, :table, :rec, :desc, :origfn, :path, :ext, :dt, :user)
    """)
    db.session.execute(sql_ins, {
        'stamp':  stamp,
        'table':  tabela,
        'rec':    rec,
        'desc':   desc,
        'origfn': filename,
        'path':   public_path,
        'ext':    ext,
        'dt':     datetime.utcnow().date(),
        'user':   user
    })
    db.session.commit()

    return jsonify({
      'success':      True,
      'ANEXOSSTAMP':  stamp,
      'FICHEIRO':     filename,
      'CAMINHO':      public_path,
      'TIPO':         ext,
      'DATA':         datetime.utcnow().isoformat(),
      'UTILIZADOR':   user
    }), 201
