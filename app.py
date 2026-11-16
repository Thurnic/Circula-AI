
from pathlib import Path
import json
import sqlite3

from flask import Flask, jsonify, render_template, request

from core.inteligencia import CirculaCore

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_DIR.mkdir(exist_ok=True)

DB_PATH = DB_DIR / "circula.db"

app = Flask(__name__)
app.json.ensure_ascii = False


def conexao():
    banco = sqlite3.connect(DB_PATH)
    banco.row_factory = sqlite3.Row
    return banco


def iniciar_banco():
    with conexao() as banco:
        banco.execute("""
            CREATE TABLE IF NOT EXISTS descartes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL,
                material TEXT NOT NULL,
                peso REAL NOT NULL,
                status TEXT NOT NULL,
                nivel TEXT NOT NULL,
                requer_avaliacao INTEGER NOT NULL,
                diagnostico TEXT NOT NULL,
                data TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify({
        "online": True,
        "sistema": "CIRCULA CORE",
        "versao": "2.0",
        "grupo": "01"
    })


@app.get("/api/embalagem/<codigo>")
def consultar(codigo):
    embalagem = CirculaCore.consultar_codigo(codigo)

    if embalagem is None:
        return jsonify({
            "erro": "Embalagem não cadastrada."
        }), 404

    return jsonify(embalagem)


@app.post("/api/analisar")
def analisar():
    dados = request.get_json(silent=True)

    try:
        resultado = CirculaCore.analisar(dados)
        return jsonify(resultado)

    except (ValueError, TypeError) as erro:
        return jsonify({"erro": str(erro)}), 400


@app.post("/api/descartes")
def cadastrar_descarte():
    dados = request.get_json(silent=True)

    try:
        # Reanalisa no servidor para não confiar
        # em diagnósticos enviados pelo navegador.
        resultado = CirculaCore.analisar(dados)

    except (ValueError, TypeError) as erro:
        return jsonify({"erro": str(erro)}), 400

    with conexao() as banco:
        cursor = banco.execute("""
            INSERT INTO descartes (
                codigo, material, peso, status,
                nivel, requer_avaliacao, diagnostico
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            resultado["codigo"],
            resultado["material_nome"],
            resultado["peso"],
            resultado["status"],
            resultado["nivel"],
            int(resultado["requer_avaliacao"]),
            json.dumps(resultado, ensure_ascii=False)
        ))

        identificador = cursor.lastrowid

    return jsonify({
        "mensagem": "Descarte registrado com sucesso.",
        "id": identificador,
        "resultado": resultado
    }), 201


@app.get("/api/descartes")
def listar_descartes():
    with conexao() as banco:
        registros = banco.execute("""
            SELECT
                id, codigo, material, peso,
                status, nivel, requer_avaliacao, data
            FROM descartes
            ORDER BY id DESC
            LIMIT 500
        """).fetchall()

    return jsonify([dict(r) for r in registros])


@app.get("/api/dashboard")
def dashboard():
    with conexao() as banco:
        resumo = banco.execute("""
            SELECT
                COUNT(*) AS quantidade,
                COALESCE(SUM(peso), 0) AS peso_total,
                COALESCE(SUM(requer_avaliacao), 0) AS alertas
            FROM descartes
        """).fetchone()

        materiais = banco.execute("""
            SELECT material, ROUND(SUM(peso), 2) AS peso
            FROM descartes
            GROUP BY material
            ORDER BY peso DESC
        """).fetchall()

    return jsonify({
        "quantidade": resumo["quantidade"],
        "peso_total": round(resumo["peso_total"], 2),
        "alertas": resumo["alertas"],
        "materiais": [dict(m) for m in materiais]
    })


@app.delete("/api/descartes")
def limpar_descartes():
    # Exclusão apenas para demonstração local.
    with conexao() as banco:
        banco.execute("DELETE FROM descartes")

    return jsonify({
        "mensagem": "Dados de demonstração apagados."
    })


if __name__ == "__main__":
    iniciar_banco()
    app.run(host="127.0.0.1", port=5000, debug=True)
