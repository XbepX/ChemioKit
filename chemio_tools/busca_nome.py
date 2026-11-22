"""
Busca de moléculas pelo nome, em camadas:

  1. glossário próprio (glossario/glossario.toml), com nomes em português;
  2. PubChem: primeiro o cache local de consultas anteriores, depois a consulta pela
     internet, com tempo limite;
  3. sugestões de nomes parecidos do glossário (erros de digitação).

O SMILES vem sempre do glossário ou do PubChem, nunca de um modelo de linguagem.
A função devolve só tipos que viram JSON, para poder virar tool do ChemioChat.
"""

import re
from concurrent.futures import TimeoutError as TempoEsgotado

from rdkit import Chem, RDLogger
from rdkit.Chem.rdMolDescriptors import CalcMolFormula

from . import cache_nomes, glossario, pubchem
from .isomeria import gerar_isomeros, interpretar_formula

LIMITE_OPCOES_FORMULA = 8  # fórmula com até 8 isômeros: mostra as opções; mais que isso, leva à Isomeria
TEMPO_LIMITE_FORMULA_BUSCA = 4.0  # segundos; a busca não pode deixar a página parada

_PADRAO_FORMULA = re.compile(r"(?:[A-Z][a-z]?\d*)+")
_CARACTERES_DE_SMILES = re.compile(r"[=#()\[\]@/\\]|[A-Za-z]\d")


def _registro_pubchem_para_opcao(registro: dict) -> dict:
    return {
        "nome": registro.get("nome_iupac") or registro.get("nome_consultado"),
        "smiles": registro["smiles"],
        "cid": registro.get("cid"),
        "nome_iupac": registro.get("nome_iupac"),
    }


def resolver_nome(nome: str, usar_pubchem: bool = True, tempo_limite: float = pubchem.TEMPO_LIMITE_PUBCHEM) -> dict:
    """
    Converte um nome de substância em SMILES. Resultados possíveis (campo "status"):

      "encontrado"           nome, smiles, fonte ("glossario" | "cache" | "pubchem") e,
                             conforme a fonte, nota, tipo_nome, cid, nome_iupac;
      "ambiguo"              opcoes: lista de {nome, smiles, ...} para o usuário escolher;
      "mistura"              nome, nota, componentes (cada um com nome e smiles), principal;
      "nao_encontrado"       sugestoes: nomes parecidos do glossário (pode ser vazia);
      "pubchem_indisponivel" motivo ("tempo_esgotado" | "sem_conexao"), mensagem e sugestoes;
      "vazio"                nenhum nome informado.
    """
    nome_limpo = nome.strip() if isinstance(nome, str) else ""
    if not nome_limpo:
        return {"status": "vazio", "mensagem": "Informe o nome da molécula."}

    # Camada 1: glossário
    no_glossario = glossario.buscar_no_glossario(nome_limpo)
    if no_glossario["status"] != "nao_encontrado":
        return {**no_glossario, "consulta": nome_limpo, "fonte": "glossario"}
    sugestoes = no_glossario["sugestoes"]

    if not usar_pubchem:
        return {"status": "nao_encontrado", "consulta": nome_limpo, "sugestoes": sugestoes}

    # Camada 2a: cache local de consultas anteriores ao PubChem
    registro = cache_nomes.obter(nome_limpo)
    if registro is not None:
        return {
            "status": "encontrado",
            "consulta": nome_limpo,
            "fonte": "cache",
            "nome": nome_limpo,
            **{k: registro[k] for k in ("smiles", "cid", "nome_iupac")},
        }

    # Camada 2b: PubChem pela internet
    try:
        candidatos = pubchem.consultar_pubchem_com_tempo_limite(nome_limpo, tempo_limite)
    except TempoEsgotado:
        return {
            "status": "pubchem_indisponivel",
            "consulta": nome_limpo,
            "motivo": "tempo_esgotado",
            "mensagem": f"O PubChem não respondeu em {tempo_limite:g} s.",
            "sugestoes": sugestoes,
        }
    except Exception as e:  # sem rede, erro HTTP, resposta inesperada
        return {
            "status": "pubchem_indisponivel",
            "consulta": nome_limpo,
            "motivo": "sem_conexao",
            "mensagem": f"Não foi possível consultar o PubChem ({type(e).__name__}).",
            "sugestoes": sugestoes,
        }

    if len(candidatos) == 1:
        cache_nomes.salvar(nome_limpo, candidatos[0])
        return {
            "status": "encontrado",
            "consulta": nome_limpo,
            "fonte": "pubchem",
            "nome": nome_limpo,
            **{k: candidatos[0][k] for k in ("smiles", "cid", "nome_iupac")},
        }
    if len(candidatos) > 1:
        # Vários registros: o usuário escolhe. Não vai para o cache, que guarda um registro por nome.
        return {
            "status": "ambiguo",
            "consulta": nome_limpo,
            "fonte": "pubchem",
            "opcoes": [_registro_pubchem_para_opcao(c) for c in candidatos],
        }

    # Camada 3: nomes parecidos no glossário
    return {"status": "nao_encontrado", "consulta": nome_limpo, "sugestoes": sugestoes}


def _parece_formula(texto: str) -> bool:
    """Escrito como fórmula molecular: só símbolos e números, cada elemento uma vez (C2H6O sim, CCO não)."""
    if not _PADRAO_FORMULA.fullmatch(texto):
        return False
    simbolos = re.findall(r"[A-Z][a-z]?", texto)
    return len(simbolos) == len(set(simbolos))


def _smiles_valido(texto: str) -> bool:
    RDLogger.DisableLog("rdApp.*")
    try:
        return Chem.MolFromSmiles(texto) is not None
    finally:
        RDLogger.EnableLog("rdApp.*")


def resolver_entrada(texto: str, usar_pubchem: bool = True, tempo_limite: float = pubchem.TEMPO_LIMITE_PUBCHEM) -> dict:
    """
    Campo único de busca: decide se o texto é nome, SMILES ou fórmula molecular, nesta ordem:
      1. nome do glossário (em português);
      2. SMILES válido;
      3. fórmula molecular (ex.: H2O, CH4, C2H6O): com um isômero, abre; com até 8, mostra
         as opções; com mais, indica a página Isomeria (status "formula");
      4. texto com cara de SMILES (parênteses, =, #, colchetes, letra seguida de número) que não
         é válido: status "smiles_invalido", sem consultar o PubChem;
      5. nome no cache ou no PubChem, e depois sugestões (resolver_nome).
    Os resultados seguem os de resolver_nome; "fonte" pode ser também "smiles" ou "formula".
    Quando um texto vale como fórmula e como SMILES (ex.: CO), sai lido como SMILES e "aviso"
    explica a outra leitura.
    """
    t = texto.strip() if isinstance(texto, str) else ""
    if not t:
        return {"status": "vazio", "mensagem": "Digite o nome, o SMILES ou a fórmula da molécula."}

    no_glossario = glossario.buscar_no_glossario(t)
    if no_glossario["status"] != "nao_encontrado":
        return {**no_glossario, "consulta": t, "fonte": "glossario"}

    formula = interpretar_formula(t) if _parece_formula(t) else {"valida": False}

    if " " not in t and _smiles_valido(t):
        resultado = {"status": "encontrado", "consulta": t, "fonte": "smiles", "nome": "", "smiles": t}
        if formula["valida"] and len(formula["elementos"]) + (1 if formula["hidrogenios"] else 0) >= 2 \
                and CalcMolFormula(Chem.MolFromSmiles(t)) != formula["formula"]:
            resultado["aviso"] = (f"“{t}” foi lido como SMILES (fórmula {CalcMolFormula(Chem.MolFromSmiles(t))}). "
                                  f"Se você quis dizer a fórmula molecular {formula['formula']}, digite o nome da substância.")
        return resultado

    if formula["valida"]:
        res = gerar_isomeros(formula["formula"], tempo_limite=TEMPO_LIMITE_FORMULA_BUSCA)
        if res["status"] == "muito_grande":
            return {"status": "formula", "consulta": t, "formula": formula["formula"], "total": -1,
                    "mensagem": f"{formula['formula']} é uma fórmula molecular com muitos isômeros possíveis."}
        if res["status"] == "ok":
            # "nome" é o rótulo do botão; "nome_molecula" é o que vai para o cartão (vazio se não houver nome)
            opcoes = [{"nome": i["nome"] or f"{i['smiles']} ({i['grupo']})", "nome_molecula": i["nome"] or "",
                       "smiles": i["smiles"], "nota": i["grupo"]} for i in res["isomeros"]]
            if len(opcoes) == 1:
                return {"status": "encontrado", "consulta": t, "fonte": "formula",
                        "nome": res["isomeros"][0]["nome"] or "", "smiles": opcoes[0]["smiles"]}
            if len(opcoes) <= LIMITE_OPCOES_FORMULA:
                return {"status": "ambiguo", "consulta": t, "fonte": "formula", "formula": res["formula"], "opcoes": opcoes}
            return {"status": "formula", "consulta": t, "formula": res["formula"], "total": res["total"],
                    "mensagem": f"{res['formula']} é uma fórmula molecular com {res['total']} isômeros possíveis."}
        return {"status": "formula", "consulta": t, "formula": formula["formula"], "total": None, "mensagem": res["mensagem"]}

    if _CARACTERES_DE_SMILES.search(t) and " " not in t:
        return {"status": "smiles_invalido", "consulta": t,
                "mensagem": f"“{t}” parece um SMILES, mas não é válido. Confira parênteses, números de anel e letras."}

    return resolver_nome(t, usar_pubchem=usar_pubchem, tempo_limite=tempo_limite)
