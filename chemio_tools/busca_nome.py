"""
Busca de moléculas pelo nome, em camadas:

  1. glossário próprio (glossario/glossario.toml), com nomes em português;
  2. PubChem: primeiro o cache local de consultas anteriores, depois a consulta pela
     internet, com tempo limite;
  3. sugestões de nomes parecidos do glossário (erros de digitação).

O SMILES vem sempre do glossário ou do PubChem, nunca de um modelo de linguagem.
A função devolve só tipos que viram JSON, para poder virar tool do ChemioChat.
"""

from concurrent.futures import TimeoutError as TempoEsgotado

from . import cache_nomes, glossario, pubchem


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
