"""
Glossário de nomes de substâncias (glossario/glossario.toml).

Liga os nomes usados por estudantes e professores (oficiais, comuns, comerciais e
informais) a uma estrutura. É a primeira camada da busca por nome, antes do PubChem.

Adaptado de ChemioChat_app/agente/glossario.py. Mudanças:
  - importa validar_smiles de .utils (o módulo agora faz parte do motor);
  - o caminho padrão aponta para a pasta glossario/ do ChemioKit;
  - buscar_no_glossario() devolve só tipos que viram JSON (dict, list, str), para
    poder virar tool do ChemioChat. As classes continuam disponíveis para uso interno.

O arquivo é conferido quando é carregado: SMILES válido no RDKit, ids únicos, componentes
de misturas existentes e tipos de nome conhecidos. Problemas são listados em vez de
derrubar o app.
"""

from __future__ import annotations

import difflib
import re
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from .utils import validar_smiles

CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "glossario" / "glossario.toml"

TIPOS_DE_NOME = {
    "iupac": "nome IUPAC",
    "comuns": "nome comum",
    "comerciais": "nome comercial",
    "informais": "nome informal",
    "ingles": "nome em inglês",
}


def normalizar(nome: str) -> str:
    """Minúsculas, sem acentos, sem pontuação e com espaços simples: "Ácido L-(+)-Tartárico" -> "acido l tartarico"."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", " ", sem_acento.lower())
    return " ".join(texto.split())


@dataclass
class Entrada:
    id: str
    nome: str
    tipo: str  # "substancia" | "mistura"
    smiles: str | None = None
    nota: str | None = None
    componentes: list[str] = field(default_factory=list)
    principal: str | None = None
    nomes: dict[str, list[str]] = field(default_factory=dict)  # tipo de nome -> nomes


@dataclass
class Correspondencia:
    entrada: Entrada
    nome_encontrado: str
    tipo_nome: str


@dataclass
class Glossario:
    entradas: dict[str, Entrada]
    indice: dict[str, list[Correspondencia]]  # nome normalizado -> correspondências
    problemas: list[str]

    @property
    def total_nomes(self) -> int:
        return len(self.indice)

    def buscar(self, nome: str) -> list[Correspondencia]:
        """Correspondências exatas (após normalizar). Mais de uma = nome ambíguo."""
        return self.indice.get(normalizar(nome), []) if nome else []

    def sugerir(self, nome: str, maximo: int = 3, corte: float = 0.9) -> list[str]:
        """
        Nomes parecidos (erros de digitação), para perguntar "você quis dizer...?".
        O corte é alto porque nomes químicos parecidos costumam ser substâncias diferentes
        (ex.: ácido etanoico x ácido butanoico).
        """
        chave = normalizar(nome or "")
        if len(chave) < 5:
            return []
        parecidos = difflib.get_close_matches(chave, list(self.indice), n=maximo, cutoff=corte)
        return [self.indice[p][0].nome_encontrado for p in parecidos]

    def componentes_de(self, entrada: Entrada) -> list[Entrada]:
        return [self.entradas[c] for c in entrada.componentes if c in self.entradas]


def carregar(caminho: Path = CAMINHO_PADRAO) -> Glossario:
    problemas: list[str] = []
    try:
        with open(caminho, "rb") as f:
            dados = tomllib.load(f)
    except FileNotFoundError:
        return Glossario({}, {}, [f"Arquivo não encontrado: {caminho}"])
    except tomllib.TOMLDecodeError as e:
        return Glossario({}, {}, [f"Erro de sintaxe no glossário: {e}"])

    entradas: dict[str, Entrada] = {}
    for tipo, chave in (("substancia", "substancia"), ("mistura", "mistura")):
        for bruto in dados.get(chave, []):
            ident = bruto.get("id")
            if not ident:
                problemas.append(f"Entrada sem id: {bruto.get('nome', bruto)}")
                continue
            if ident in entradas:
                problemas.append(f"id repetido: {ident}")
                continue
            desconhecidos = set(bruto) - {"id", "nome", "smiles", "nota", "componentes", "principal"} - set(TIPOS_DE_NOME)
            if desconhecidos:
                problemas.append(f"{ident}: campo(s) desconhecido(s) {sorted(desconhecidos)}")
            entrada = Entrada(
                id=ident,
                nome=bruto.get("nome", ident),
                tipo=tipo,
                smiles=bruto.get("smiles"),
                nota=bruto.get("nota"),
                componentes=list(bruto.get("componentes", [])),
                principal=bruto.get("principal"),
                nomes={t: list(bruto.get(t, [])) for t in TIPOS_DE_NOME if bruto.get(t)},
            )
            if tipo == "substancia" and not (entrada.smiles and validar_smiles(entrada.smiles)):
                problemas.append(f"{ident}: SMILES ausente ou inválido ({entrada.smiles!r})")
                continue
            if not entrada.nomes:
                problemas.append(f"{ident}: nenhum nome cadastrado")
            entradas[ident] = entrada

    for entrada in entradas.values():
        if entrada.tipo != "mistura":
            continue
        for c in entrada.componentes:
            if c not in entradas or entradas[c].tipo != "substancia":
                problemas.append(f"{entrada.id}: componente desconhecido '{c}'")
        if entrada.principal and entrada.principal not in entrada.componentes:
            problemas.append(f"{entrada.id}: principal '{entrada.principal}' não está entre os componentes")

    indice: dict[str, list[Correspondencia]] = {}
    for entrada in entradas.values():
        vistos = set()
        for tipo_nome, nomes in entrada.nomes.items():
            for nome in nomes:
                chave = normalizar(nome)
                if not chave or chave in vistos:
                    continue
                vistos.add(chave)
                indice.setdefault(chave, []).append(Correspondencia(entrada, nome, TIPOS_DE_NOME[tipo_nome]))

    return Glossario(entradas, indice, problemas)


_glossario: Glossario | None = None


def obter() -> Glossario:
    """Glossário carregado uma vez por processo (recarregue com recarregar())."""
    global _glossario
    if _glossario is None:
        _glossario = carregar()
    return _glossario


def recarregar() -> Glossario:
    global _glossario
    _glossario = carregar()
    return _glossario


# ------------------------------------------------------------------ saída em JSON


def _entrada_para_dict(e: Entrada) -> dict:
    return {"id": e.id, "nome": e.nome, "smiles": e.smiles, "nota": e.nota}


def buscar_no_glossario(nome: str) -> dict:
    """
    Procura o nome no glossário e devolve um dict que vira JSON:
      {"status": "encontrado", "nome", "smiles", "nota", "tipo_nome", "id"}
      {"status": "ambiguo",    "opcoes": [{"id", "nome", "smiles", "nota"}, ...]}
      {"status": "mistura",    "nome", "nota", "componentes": [...], "principal": id | None}
      {"status": "nao_encontrado", "sugestoes": [nomes parecidos]}
    """
    g = obter()
    correspondencias = g.buscar(nome)
    if not correspondencias:
        return {"status": "nao_encontrado", "sugestoes": g.sugerir(nome)}

    entradas = list({c.entrada.id: c.entrada for c in correspondencias}.values())
    if len(entradas) > 1:
        return {"status": "ambiguo", "opcoes": [_entrada_para_dict(e) for e in entradas]}

    c = correspondencias[0]
    e = c.entrada
    if e.tipo == "mistura":
        return {
            "status": "mistura",
            "id": e.id,
            "nome": e.nome,
            "nota": e.nota,
            "componentes": [_entrada_para_dict(x) for x in g.componentes_de(e)],
            "principal": e.principal,
        }
    return {"status": "encontrado", **_entrada_para_dict(e), "tipo_nome": c.tipo_nome}
