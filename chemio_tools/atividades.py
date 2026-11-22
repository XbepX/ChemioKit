"""
Atividades para estudantes, geradas pelo próprio motor para qualquer molécula.

gerar_atividade(tipo, smiles) devolve o enunciado, as opções e a resposta esperada;
corrigir_atividade(atividade, resposta) confere a resposta do estudante e devolve o que
acertou, o que errou e a explicação. Nada é gravado: as respostas existem só na sessão.

Tipos:
  "quirais"      quais carbonos são quirais
  "hibridizacao" hibridização de cada carbono (sp³, sp², sp)
  "sigma_pi"     número de ligações σ e π
  "cadeia"       classificação da cadeia (aberta/fechada, normal/ramificada, ...)
  "isomeria"     tipo de isomeria entre duas estruturas
"""

from __future__ import annotations

import random
from functools import lru_cache

from rdkit import Chem
from rdkit.Chem.rdMolDescriptors import CalcMolFormula

from . import glossario
from .explicacoes import (
    explicar_cadeia,
    explicar_carbonos_quirais,
    explicar_hibridizacao,
    explicar_ligacoes_sigma_pi,
)
from .isomeria import classificar_par_isomeros, gerar_isomeros
from .utils import obter_mapa_carbonos, validar_smiles

TIPOS_ATIVIDADE = {
    "quirais": "Carbonos quirais",
    "hibridizacao": "Hibridização dos carbonos",
    "sigma_pi": "Ligações σ e π",
    "cadeia": "Classificação da cadeia",
    "isomeria": "Tipo de isomeria",
}

LIMITE_CARBONOS_HIBRIDIZACAO = 12
# Prática de isomeria: fórmulas pequenas, com poucos isômeros (pares reconhecíveis em sala)
LIMITE_ATOMOS_PRATICA_ISOMERIA = 6
LIMITE_ISOMEROS_PRATICA = 30
TIPOS_ISOMERIA_PLANA = ["função", "cadeia", "posição", "metameria", "tautomeria"]
TIPOS_ISOMERIA_ESPACIAL = ["geométrica", "óptica"]

PERGUNTAS_CADEIA = [
    ("aberta/fechada", "A cadeia é aberta ou fechada?", ["aberta", "fechada"]),
    ("normal/ramificada", "A cadeia é normal ou ramificada?", ["normal", "ramificada"]),
    ("homogênea/heterogênea", "A cadeia é homogênea ou heterogênea?", ["homogênea", "heterogênea"]),
    ("saturada/insaturada", "A cadeia é saturada ou insaturada?", ["saturada", "insaturada"]),
]


def _simplificar_cadeia(valor: str) -> str:
    """'fechada (aromática)' -> 'fechada'; 'não ramificada' (anel sem ramo) -> 'normal'."""
    return {"fechada (aromática)": "fechada", "não ramificada": "normal"}.get(valor, valor)


def gerar_atividade(tipo: str, smiles: str, smiles_b: str | None = None, semente: int = 0) -> dict | None:
    """
    Monta a atividade. Devolve None se o SMILES for inválido ou se a molécula não servir
    para o tipo (ex.: sem carbono). Para "isomeria", sem smiles_b, escolhe outro isômero
    da mesma fórmula (até 8 átomos além do H) com a semente dada.
    """
    if tipo not in TIPOS_ATIVIDADE or not validar_smiles(smiles):
        return None
    mol = Chem.MolFromSmiles(smiles.strip())
    mapa = obter_mapa_carbonos(mol)
    if not mapa:
        return None
    base = {"tipo": tipo, "titulo": TIPOS_ATIVIDADE[tipo], "smiles": smiles.strip()}

    if tipo == "quirais":
        exp = explicar_carbonos_quirais(smiles)
        return {
            **base,
            "enunciado": "Quais carbonos são quirais (ligados a quatro ligantes diferentes)? "
            "Marque todos. Se não houver, marque “Nenhum”.",
            "opcoes": list(mapa.values()),
            "resposta": sorted((c["rotulo"] for c in exp["centros"]), key=lambda r: int(r[1:]) if r[1:].isdigit() else 0),
            "explicacao": [exp["texto"]] + [c["texto"] for c in exp["centros"]],
            "dica": "Para cada carbono, liste os quatro grupos ligados a ele (contando os H). "
            "Carbono com dupla ou com dois H iguais não pode ser quiral.",
        }

    if tipo == "hibridizacao":
        exp = explicar_hibridizacao(smiles)
        carbonos = exp["carbonos"]
        if len(carbonos) > LIMITE_CARBONOS_HIBRIDIZACAO:
            carbonos = sorted(random.Random(semente).sample(carbonos, LIMITE_CARBONOS_HIBRIDIZACAO), key=lambda c: c["indice_rdkit"])
        return {
            **base,
            "enunciado": "Qual é a hibridização de cada carbono?",
            "itens": [c["rotulo"] for c in carbonos],
            "opcoes": ["sp3", "sp2", "sp"],
            "resposta": {c["rotulo"]: c["hibridizacao"] for c in carbonos},
            "explicacao": [exp["regra"]] + [c["texto"] for c in carbonos],
            "dica": exp["regra"],
        }

    if tipo == "sigma_pi":
        exp = explicar_ligacoes_sigma_pi(smiles)
        return {
            **base,
            "enunciado": "Quantas ligações σ (sigma) e π (pi) há na molécula? Conte também as ligações com hidrogênio.",
            "resposta": {"sigma": exp["sigma"], "pi": exp["pi"]},
            "explicacao": [exp["regra"], exp["texto"]],
            "dica": exp["regra"],
        }

    if tipo == "cadeia":
        exp = explicar_cadeia(smiles)
        motivos = {i["atributo"]: i["motivo"] for i in exp["itens"]}
        return {
            **base,
            "enunciado": "Classifique a cadeia carbônica.",
            "perguntas": [{"atributo": a, "pergunta": p, "opcoes": o} for a, p, o in PERGUNTAS_CADEIA],
            "resposta": {a: _simplificar_cadeia(exp["classificacao"][a]) for a, _, _ in PERGUNTAS_CADEIA},
            "explicacao": [f"{_simplificar_cadeia(exp['classificacao'][a]).capitalize()}: {motivos[a]}" for a, _, _ in PERGUNTAS_CADEIA],
            "dica": "Cadeia heterogênea tem heteroátomo (O, N, S) ENTRE carbonos; um OH na ponta não conta.",
        }

    # tipo == "isomeria"
    if smiles_b is None:
        res = gerar_isomeros(CalcMolFormula(mol), tempo_limite=5)
        if res["status"] != "ok":
            return None
        proprio = Chem.MolToSmiles(mol, isomericSmiles=False)
        outros = [i["smiles"] for i in res["isomeros"] if i["smiles"] != proprio]
        if not outros:
            return None
        smiles_b = random.Random(semente).choice(outros)
    if not validar_smiles(smiles_b):
        return None
    par = classificar_par_isomeros(smiles, smiles_b)
    if par["relacao"] not in ("plana", "espacial"):
        return None
    opcoes = TIPOS_ISOMERIA_PLANA if par["relacao"] == "plana" else TIPOS_ISOMERIA_ESPACIAL
    return {
        **base,
        "smiles_b": smiles_b,
        "enunciado": "Qual é o tipo de isomeria entre as duas estruturas?",
        "opcoes": opcoes,
        "resposta": par["tipo"],
        "explicacao": [f"Isomeria {par['relacao']}: {par['tipo']}" + (f" ({par['subtipo']})." if par["subtipo"] else "."), par["explicacao"]],
        "dica": "Compare nesta ordem: as funções são as mesmas? A cadeia é do mesmo tipo? "
        "Muda só a posição de um grupo, ou de um heteroátomo?",
    }


def itens_sem_resposta(atividade: dict, resposta: object) -> list[str]:
    """
    O que o estudante ainda não respondeu (lista vazia = pode corrigir). Para "quirais",
    None significa "nada marcado"; lista vazia significa que marcou "Nenhum".
    """
    tipo = atividade["tipo"]
    if tipo == "quirais":
        return ["marque os carbonos quirais ou “Nenhum”"] if resposta is None else []
    if tipo == "hibridizacao":
        resposta = resposta or {}
        return [item for item in atividade["itens"] if resposta.get(item) is None]
    if tipo == "sigma_pi":
        resposta = resposta or {}
        return [nome for chave, nome in (("sigma", "ligações σ"), ("pi", "ligações π")) if resposta.get(chave) is None]
    if tipo == "cadeia":
        resposta = resposta or {}
        return [p["pergunta"] for p in atividade["perguntas"] if resposta.get(p["atributo"]) is None]
    return ["escolha o tipo de isomeria"] if resposta is None else []


def corrigir_atividade(atividade: dict, resposta: object) -> dict:
    """
    Confere a resposta do estudante. Formatos de resposta:
      quirais:      lista de rótulos (["C2"]; lista vazia = "Nenhum")
      hibridizacao: {"C1": "sp3", ...}
      sigma_pi:     {"sigma": n, "pi": n}
      cadeia:       {"aberta/fechada": "aberta", ...}
      isomeria:     "posição"
    Devolve {"correto", "itens": [{item, resposta, esperado, correto}], "explicacao"}.
    """
    tipo = atividade["tipo"]
    esperado = atividade["resposta"]
    itens = []

    if tipo == "quirais":
        marcados = set(resposta or [])
        certos = set(esperado)
        for rotulo in atividade["opcoes"]:
            if rotulo in marcados or rotulo in certos:
                itens.append({"item": rotulo, "resposta": rotulo in marcados, "esperado": rotulo in certos,
                              "correto": (rotulo in marcados) == (rotulo in certos)})
        correto = marcados == certos
    elif tipo in ("hibridizacao", "sigma_pi", "cadeia"):
        resposta = resposta or {}
        for chave, valor in esperado.items():
            dado = resposta.get(chave)
            itens.append({"item": chave, "resposta": dado, "esperado": valor, "correto": dado == valor})
        correto = all(i["correto"] for i in itens)
    else:  # isomeria
        correto = resposta == esperado
        itens.append({"item": "tipo", "resposta": resposta, "esperado": esperado, "correto": correto})

    return {"correto": correto, "itens": itens, "explicacao": atividade["explicacao"]}


# ------------------------------------------------------------------ moléculas para praticar


@lru_cache(maxsize=256)
def _total_isomeros(formula: str) -> int:
    res = gerar_isomeros(formula, tempo_limite=5)
    return res["total"] if res["status"] == "ok" else 0


def moleculas_para_praticar(tipo: str) -> list[dict]:
    """
    Substâncias do glossário adequadas ao tipo de atividade ({"nome", "smiles"}):
    de 2 a 12 carbonos. Para "isomeria": até 6 átomos além do H e fórmula com 2 a 30
    isômeros, para que o par sorteado seja reconhecível em sala.
    """
    lista = []
    for e in glossario.obter().entradas.values():
        if e.tipo != "substancia":
            continue
        mol = Chem.MolFromSmiles(e.smiles)
        carbonos = sum(a.GetSymbol() == "C" for a in mol.GetAtoms())
        if not 2 <= carbonos <= 12 or "." in e.smiles:
            continue
        if tipo == "isomeria" and mol.GetNumAtoms() > LIMITE_ATOMOS_PRATICA_ISOMERIA:
            continue
        if tipo == "isomeria" and any(a.GetSymbol() not in ("C", "N", "O", "S", "F", "Cl", "Br", "I") for a in mol.GetAtoms()):
            continue
        if any(a.GetFormalCharge() for a in mol.GetAtoms()):
            continue
        if tipo == "isomeria" and not 2 <= _total_isomeros(CalcMolFormula(mol)) <= LIMITE_ISOMEROS_PRATICA:
            continue
        lista.append({"nome": e.nome, "smiles": e.smiles})
    return lista
