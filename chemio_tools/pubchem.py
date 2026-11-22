"""
Conversão de nomes de moléculas em SMILES por consulta ao PubChem (PubChemPy).

Adaptado de ChemioChat_app/chemio_tools/pubchem.py. Mudanças:
  - consultar_pubchem_com_tempo_limite(): o PubChemPy não define tempo limite para a
    conexão (chama urlopen sem timeout). A consulta roda numa thread separada e quem
    chamou desiste depois de `tempo_limite` segundos, sem travar o app;
  - a função de verificação de registros (obter_registro_pubchem), usada só pelo agente
    do ChemioChat, não foi trazida.

Diferente das outras funções do motor, estas dependem de um serviço externo e de
conexão com a internet. Por isso distinguem os casos sem resultado:
  - nome não encontrado no PubChem      -> lista vazia;
  - falha de rede ou PubChem fora do ar -> a exceção é propagada para quem chamou;
  - PubChem lento                        -> concurrent.futures.TimeoutError.
"""

from concurrent.futures import ThreadPoolExecutor

import pubchempy as pcp

from .utils import validar_smiles

TEMPO_LIMITE_PUBCHEM = 8.0  # segundos


def buscar_candidatos_por_nome(nome: str, maximo: int = 5) -> list[dict]:
    """
    Consulta o PubChem pelo nome e devolve até `maximo` registros com SMILES válido.
    Mais de um registro indica que o nome é ambíguo no PubChem.

    O PubChem indexa sobretudo nomes em inglês (ex.: "aspirin", "lactic acid"), mas
    também muitos sinônimos, nomes comerciais e números CAS. O SMILES devolvido é o
    "absoluto" do PubChem (com estereoquímica, quando definida) e é conferido com
    validar_smiles antes de ser aceito.
    """
    if not nome or not nome.strip():
        return []

    nome_limpo = nome.strip()
    candidatos = []
    vistos = set()
    for composto in pcp.get_compounds(nome_limpo, "name"):
        smiles = composto.smiles
        if smiles and validar_smiles(smiles) and smiles not in vistos:
            vistos.add(smiles)
            candidatos.append(
                {
                    "nome_consultado": nome_limpo,
                    "smiles": smiles,
                    "cid": composto.cid,
                    "nome_iupac": composto.iupac_name,
                }
            )
        if len(candidatos) >= maximo:
            break
    return candidatos


def consultar_pubchem_com_tempo_limite(nome: str, tempo_limite: float = TEMPO_LIMITE_PUBCHEM) -> list[dict]:
    """
    Igual a buscar_candidatos_por_nome, mas desiste depois de `tempo_limite` segundos
    (levanta concurrent.futures.TimeoutError). A thread da consulta é abandonada e
    termina sozinha quando a conexão cair.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        return executor.submit(buscar_candidatos_por_nome, nome).result(timeout=tempo_limite)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
