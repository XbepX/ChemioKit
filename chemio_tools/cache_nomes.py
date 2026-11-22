"""
Cache local das consultas ao PubChem (nomes e fórmulas).

Adaptado de ChemioChat_app/agente/cache_nomes.py. Guarda apenas consultas
bem-sucedidas, para que funcionem depois sem internet:
  - nomes -> SMILES (só quando o PubChem devolveu um único registro);
  - fórmula -> nomes dos compostos com essa fórmula (ambiente de isomeria).
A tabela de registros de verificação do ChemioChat não foi trazida.

O arquivo fica em dados/cache_nomes.sqlite (pasta ignorada pelo git). Qualquer falha
de leitura ou gravação é ignorada: o cache é opcional.
"""

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path

CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "dados" / "cache_nomes.sqlite"

# Pode ser trocado nos testes (monkeypatch) para um arquivo temporário.
caminho_cache: Path = CAMINHO_PADRAO


def _conectar() -> sqlite3.Connection:
    caminho_cache.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho_cache)
    conexao.execute(
        """CREATE TABLE IF NOT EXISTS nomes (
               chave TEXT PRIMARY KEY,
               nome_consultado TEXT NOT NULL,
               smiles TEXT NOT NULL,
               cid INTEGER,
               nome_iupac TEXT,
               gravado_em REAL NOT NULL
           )"""
    )
    conexao.execute(
        """CREATE TABLE IF NOT EXISTS formulas (
               formula TEXT PRIMARY KEY,
               nomes TEXT NOT NULL,
               gravado_em REAL NOT NULL
           )"""
    )
    return conexao


def _chave(nome: str) -> str:
    return " ".join(nome.strip().lower().split())


def obter(nome: str) -> dict | None:
    """Devolve o registro guardado para o nome, ou None se ele ainda não foi consultado."""
    try:
        with closing(_conectar()) as conexao, conexao:
            linha = conexao.execute(
                "SELECT nome_consultado, smiles, cid, nome_iupac FROM nomes WHERE chave = ?",
                (_chave(nome),),
            ).fetchone()
    except (sqlite3.Error, OSError):
        return None
    if linha is None:
        return None
    return {"nome_consultado": linha[0], "smiles": linha[1], "cid": linha[2], "nome_iupac": linha[3]}


def salvar(nome: str, registro: dict) -> None:
    """Guarda um resultado do PubChem. Falhas de gravação são ignoradas (o cache é opcional)."""
    try:
        with closing(_conectar()) as conexao, conexao:
            conexao.execute(
                "INSERT OR REPLACE INTO nomes VALUES (?, ?, ?, ?, ?, ?)",
                (
                    _chave(nome),
                    registro["nome_consultado"],
                    registro["smiles"],
                    registro.get("cid"),
                    registro.get("nome_iupac"),
                    time.time(),
                ),
            )
    except (sqlite3.Error, OSError):
        pass


def obter_formula(formula: str) -> dict | None:
    """Nomes guardados para a fórmula (bloco do InChIKey -> {cid, nome}), ou None."""
    try:
        with closing(_conectar()) as conexao, conexao:
            linha = conexao.execute("SELECT nomes FROM formulas WHERE formula = ?", (formula.strip(),)).fetchone()
    except (sqlite3.Error, OSError):
        return None
    return json.loads(linha[0]) if linha else None


def salvar_formula(formula: str, nomes: dict) -> None:
    try:
        with closing(_conectar()) as conexao, conexao:
            conexao.execute(
                "INSERT OR REPLACE INTO formulas VALUES (?, ?, ?)",
                (formula.strip(), json.dumps(nomes, ensure_ascii=False), time.time()),
            )
    except (sqlite3.Error, OSError):
        pass
