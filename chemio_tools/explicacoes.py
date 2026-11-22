"""
Explicações didáticas ("Por quê?") dos resultados do motor.

Cada função recebe um SMILES e devolve textos em português, prontos para mostrar a
estudantes, junto com os dados usados para chegar a eles. Os textos seguem o que o
motor calculou (RDKit); nenhuma regra é aplicada sem conferir na molécula.
"""

from __future__ import annotations

from rdkit import Chem

from .isomeria import _atomos_da_cadeia, classificar_cadeia
from .ligacoes import analisar_hibridizacao_e_ligacoes
from .stereochemistry import _gerar_imagem_especular, identificar_centros_quirais
from .utils import obter_mapa_carbonos, validar_smiles

# Grupos escritos como nos livros (SMILES do ramo, a partir do átomo ligado ao centro)
NOTACAO_GRUPOS = {
    "C": "CH₃",
    "CC": "CH₂CH₃",
    "CCC": "CH₂CH₂CH₃",
    "C(C)C": "CH(CH₃)₂",
    "CCCC": "CH₂CH₂CH₂CH₃",
    "O": "OH",
    "OC": "OCH₃",
    "N": "NH₂",
    "C(=O)O": "COOH",
    "C=O": "CHO",
    "CO": "CH₂OH",
    "C(C)=O": "COCH₃",
    "C(=O)OC": "COOCH₃",
    "C#N": "CN",
    "C=C": "CH=CH₂",
    "C#C": "C≡CH",
    "c1ccccc1": "C₆H₅",
    "C1CCCCC1": "C₆H₁₁",
    "S": "SH",
    "F": "F", "Cl": "Cl", "Br": "Br", "I": "I",
}

_HIB = {Chem.HybridizationType.SP3: "sp3", Chem.HybridizationType.SP2: "sp2", Chem.HybridizationType.SP: "sp"}
ROTULO_HIB = {"sp3": "sp³", "sp2": "sp²", "sp": "sp"}


def _mol(smiles: str) -> Chem.Mol | None:
    return Chem.MolFromSmiles(smiles.strip()) if validar_smiles(smiles) else None


def _juntar(itens: list[str]) -> str:
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


# ------------------------------------------------------------------ carbonos quirais


def _ramo(mol: Chem.Mol, centro: int, vizinho: int) -> set[int]:
    vistos, pilha = set(), [vizinho]
    while pilha:
        x = pilha.pop()
        if x in vistos or x == centro:
            continue
        vistos.add(x)
        pilha.extend(n.GetIdx() for n in mol.GetAtomWithIdx(x).GetNeighbors())
    return vistos


_SUBSCRITO = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def _rotulo_atomo(atomo: Chem.Atom) -> str:
    h = atomo.GetTotalNumHs()
    return atomo.GetSymbol() + ("H" + (str(h) if h > 1 else "") if h else "").translate(_SUBSCRITO)


def _condensada(mol: Chem.Mol, raiz: int, pai: int, permitidos: set[int]) -> str:
    """Fórmula condensada de um ramo acíclico, como nos livros: CH(OH)COOH, CH₂CH₃..."""
    sub = _ramo(mol, pai, raiz) & permitidos
    smiles = Chem.MolFragmentToSmiles(mol, atomsToUse=sorted(sub), rootedAtAtom=raiz, canonical=True)
    if smiles in NOTACAO_GRUPOS:
        return NOTACAO_GRUPOS[smiles]
    atomo = mol.GetAtomWithIdx(raiz)
    if atomo.IsInRing():
        return smiles  # anéis que não estão na tabela ficam em SMILES
    filhos = [v.GetIdx() for v in atomo.GetNeighbors() if v.GetIdx() != pai and v.GetIdx() in permitidos]
    terminais = [f for f in filhos if mol.GetAtomWithIdx(f).GetDegree() == 1]
    cadeia = [f for f in filhos if f not in terminais]
    texto = _rotulo_atomo(atomo)
    for f in terminais:
        ligacao = mol.GetBondBetweenAtoms(raiz, f).GetBondType()
        prefixo = {Chem.BondType.DOUBLE: "=", Chem.BondType.TRIPLE: "≡"}.get(ligacao, "")
        texto += f"({prefixo}{_rotulo_atomo(mol.GetAtomWithIdx(f))})"
    for k, f in enumerate(cadeia):
        parte = _condensada(mol, f, raiz, permitidos)
        texto += parte if k == len(cadeia) - 1 else f"({parte})"
    return texto


def descrever_ligantes(mol: Chem.Mol, centro: int) -> list[str]:
    """Os ligantes de um átomo, escritos como nos livros quando possível (H, OH, CH₃, COOH...)."""
    mapa = obter_mapa_carbonos(mol)
    ligantes = ["H"] * mol.GetAtomWithIdx(centro).GetTotalNumHs()
    for vizinho in mol.GetAtomWithIdx(centro).GetNeighbors():
        v = vizinho.GetIdx()
        if mol.GetBondBetweenAtoms(centro, v).IsInRing():
            ligantes.append(f"anel, sentido de {mapa.get(v, vizinho.GetSymbol())}")
        else:
            ligantes.append(_condensada(mol, v, centro, _ramo(mol, centro, v)))
    return ligantes


def explicar_carbonos_quirais(smiles: str) -> dict | None:
    """
    Para cada estereocentro: rótulo (C1, C2...), configuração R/S e os quatro ligantes.
    {"centros": [{rotulo, indice_rdkit, configuracao, ligantes, texto}], "texto"}
    """
    mol = _mol(smiles)
    if mol is None:
        return None
    dados = identificar_centros_quirais(smiles)
    mapa = obter_mapa_carbonos(mol)
    centros = []
    for c in dados["centros"]:
        idx = c["indice_rdkit"]
        ligantes = descrever_ligantes(mol, idx)
        rotulo = mapa.get(idx, f"{c['elemento']}{idx}")
        config = c["configuracao"] if c["configuracao"] in ("R", "S") else None
        texto = f"{rotulo} é um carbono quiral (estereocentro): está ligado a quatro ligantes diferentes ({_juntar(ligantes)})."
        if any(lig.startswith("anel, sentido") for lig in ligantes):
            texto += " Num anel, os dois caminhos contam como ligantes diferentes quando os átomos encontrados em cada sentido são diferentes."
        if config:
            texto += f" Configuração {config} pelas regras de Cahn-Ingold-Prelog."
        else:
            texto += " A configuração (R ou S) não foi definida no SMILES."
        centros.append({"rotulo": rotulo, "indice_rdkit": idx, "configuracao": config, "ligantes": ligantes, "texto": texto})
    if not centros:
        texto = "Nenhum carbono está ligado a quatro ligantes diferentes: a molécula não tem carbono quiral."
    else:
        texto = f"{len(centros)} carbono(s) quiral(is): " + ", ".join(c["rotulo"] for c in centros) + "."
    return {"centros": centros, "texto": texto}


def explicar_atividade_optica(smiles: str) -> dict | None:
    """Texto que justifica a classificação de atividade óptica do motor."""
    if not validar_smiles(smiles):
        return None
    dados = identificar_centros_quirais(smiles)
    atividade = dados["atividade_optica"]
    textos = {
        "Opticamente Ativa": "A molécula não é igual à sua imagem especular (é quiral). Por isso desvia o plano da luz "
        "polarizada. A imagem especular é o enantiômero: desvia a luz no mesmo ângulo, no sentido oposto.",
        "Inativa (composto meso)": "A molécula tem carbonos quirais, mas é igual à sua imagem especular: há simetria interna "
        "(uma metade é o reflexo da outra). Os efeitos das duas metades se cancelam e ela não desvia a luz polarizada.",
        "Inativa": "A molécula é igual à sua imagem especular (é aquiral). Não desvia a luz polarizada.",
        "Indefinida": "Há carbonos quirais sem configuração definida no SMILES. A estrutura pode ser qualquer um dos "
        "estereoisômeros, ou uma mistura deles. Escolha um estereoisômero na galeria para classificar.",
    }
    return {"atividade_optica": atividade, "texto": textos[atividade]}


def obter_enantiomero(smiles: str) -> str | None:
    """SMILES da imagem especular, se ela for uma molécula diferente (senão None)."""
    mol = _mol(smiles)
    if mol is None:
        return None
    original = Chem.MolToSmiles(mol)
    espelho = Chem.MolToSmiles(_gerar_imagem_especular(mol))
    return espelho if espelho != original else None


# ------------------------------------------------------------------ hibridização e σ/π


def explicar_hibridizacao(smiles: str) -> dict | None:
    """
    Para cada carbono: tipos de ligação (após kekulizar) e a regra usada nos livros:
    só simples -> sp³; uma dupla -> sp²; uma tripla ou duas duplas -> sp.
    """
    mol = _mol(smiles)
    if mol is None:
        return None
    mapa = obter_mapa_carbonos(mol)
    mol_k = Chem.Mol(mol)
    Chem.Kekulize(mol_k, clearAromaticFlags=False)
    carbonos = []
    for atomo in mol.GetAtoms():
        if atomo.GetSymbol() != "C":
            continue
        idx = atomo.GetIdx()
        ak = mol_k.GetAtomWithIdx(idx)
        duplas = sum(1 for b in ak.GetBonds() if b.GetBondType() == Chem.BondType.DOUBLE)
        triplas = sum(1 for b in ak.GetBonds() if b.GetBondType() == Chem.BondType.TRIPLE)
        hib = _HIB.get(atomo.GetHybridization(), str(atomo.GetHybridization()))
        if triplas:
            motivo = "faz uma ligação tripla"
        elif duplas >= 2:
            motivo = "faz duas ligações duplas"
        elif duplas == 1:
            motivo = "faz uma ligação dupla" + (" (no anel aromático, as duplas se alternam)" if atomo.GetIsAromatic() else "")
        else:
            motivo = "faz só ligações simples"
        carbonos.append(
            {
                "rotulo": mapa[idx],
                "indice_rdkit": idx,
                "hibridizacao": hib,
                "duplas": duplas,
                "triplas": triplas,
                "texto": f"{mapa[idx]} {motivo}: {ROTULO_HIB.get(hib, hib)}.",
            }
        )
    regra = "Só ligações simples: sp³. Uma ligação dupla: sp². Uma tripla ou duas duplas: sp."
    return {"carbonos": carbonos, "regra": regra}


def explicar_ligacoes_sigma_pi(smiles: str) -> dict | None:
    dados = analisar_hibridizacao_e_ligacoes(smiles)
    if dados is None:
        return None
    lig = dados["ligacoes"]
    texto = (
        f"Simples: {lig['simples']} ({lig['simples']} σ). "
        f"Duplas: {lig['duplas']} ({lig['duplas']} σ + {lig['duplas']} π). "
        f"Triplas: {lig['triplas']} ({lig['triplas']} σ + {2 * lig['triplas']} π). "
        f"Total: {dados['sigma']} σ e {dados['pi']} π."
    )
    regra = "Toda ligação tem 1 σ. A dupla tem também 1 π; a tripla, 2 π. Contam-se as ligações com H, e o anel aromático entra com duplas alternadas."
    return {"sigma": dados["sigma"], "pi": dados["pi"], "ligacoes": lig, "texto": texto, "regra": regra}


# ------------------------------------------------------------------ cadeia carbônica


def explicar_cadeia(smiles: str) -> dict | None:
    """Classificação escolar da cadeia com o motivo de cada característica."""
    mol = _mol(smiles)
    if mol is None:
        return None
    c = classificar_cadeia(mol)
    mapa = obter_mapa_carbonos(mol)
    info = mol.GetRingInfo()
    itens = []

    if c["aberta"]:
        itens.append({"atributo": "aberta/fechada", "valor": "aberta", "motivo": "Não há anel: as extremidades da cadeia não se unem."})
    else:
        tamanhos = sorted({len(r) for r in info.AtomRings()})
        valor = "fechada (aromática)" if c["aromatica"] else "fechada"
        itens.append({"atributo": "aberta/fechada", "valor": valor,
                      "motivo": f"Há anel de {', '.join(map(str, tamanhos))} átomos." + (" O anel é aromático." if c["aromatica"] else "")})

    if c["ramificada"]:
        if c["aberta"]:
            cadeia = _atomos_da_cadeia(mol)
            ponto = next(
                (mapa.get(i, mol.GetAtomWithIdx(i).GetSymbol()) for i in sorted(cadeia)
                 if sum(v.GetIdx() in cadeia for v in mol.GetAtomWithIdx(i).GetNeighbors()) >= 3),
                None,
            )
            motivo = f"{ponto} está ligado a três ou mais átomos da cadeia." if ponto else "Há um átomo da cadeia ligado a três ou mais outros."
        else:
            motivo = "O anel tem pelo menos um ramo (cadeia lateral)."
        itens.append({"atributo": "normal/ramificada", "valor": "ramificada", "motivo": motivo})
    else:
        itens.append({"atributo": "normal/ramificada", "valor": "normal" if c["aberta"] else "não ramificada",
                      "motivo": "Nenhum átomo da cadeia está ligado a mais de dois outros." if c["aberta"] else "O anel não tem ramos."})

    if c["heterogenea"]:
        hetero = sorted({a.GetSymbol() for a in mol.GetAtoms() if a.GetSymbol() in ("O", "N", "S")
                         and sum(v.GetSymbol() == "C" for v in a.GetNeighbors()) >= 2})
        itens.append({"atributo": "homogênea/heterogênea", "valor": "heterogênea",
                      "motivo": f"Há heteroátomo ({', '.join(hetero)}) entre dois carbonos."})
    else:
        itens.append({"atributo": "homogênea/heterogênea", "valor": "homogênea",
                      "motivo": "Não há heteroátomo entre carbonos (grupos como OH na ponta não contam)."})

    if c["insaturada"]:
        itens.append({"atributo": "saturada/insaturada", "valor": "insaturada",
                      "motivo": "Há ligação dupla, tripla ou aromática entre carbonos."})
    else:
        itens.append({"atributo": "saturada/insaturada", "valor": "saturada",
                      "motivo": "Entre carbonos só há ligações simples."})
    return {"itens": itens, "classificacao": {i["atributo"]: i["valor"] for i in itens}}
