from rdkit import Chem
from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers, StereoEnumerationOptions, GetStereoisomerCount
from .utils import validar_smiles, obter_mapa_carbonos


def _gerar_imagem_especular(mol: Chem.Mol) -> Chem.Mol:
    """Retorna uma cópia da molécula com todas as tags quirais tetraédricas invertidas (enantiômero)."""
    espelho = Chem.Mol(mol)
    for atomo in espelho.GetAtoms():
        tag = atomo.GetChiralTag()
        if tag == Chem.ChiralType.CHI_TETRAHEDRAL_CW:
            atomo.SetChiralTag(Chem.ChiralType.CHI_TETRAHEDRAL_CCW)
        elif tag == Chem.ChiralType.CHI_TETRAHEDRAL_CCW:
            atomo.SetChiralTag(Chem.ChiralType.CHI_TETRAHEDRAL_CW)
    return espelho


def classificar_atividade_optica(mol: Chem.Mol, centros: list[tuple[int, str]]) -> str:
    """
    Classifica a atividade óptica a partir dos centros quirais (saída de FindMolChiralCenters).
    - Algum centro sem configuração ("?")          -> "Indefinida"
    - SMILES canônico igual ao da imagem especular -> "Inativa (composto meso)" (com centros) ou "Inativa"
    - SMILES canônico diferente da imagem especular -> "Opticamente Ativa"
    """
    if any(config == "?" for _, config in centros):
        return "Indefinida"

    smiles_original = Chem.MolToSmiles(mol)
    smiles_espelho = Chem.MolToSmiles(_gerar_imagem_especular(mol))

    if smiles_original == smiles_espelho:
        return "Inativa (composto meso)" if centros else "Inativa"
    return "Opticamente Ativa"


def identificar_centros_quirais(smiles: str) -> dict | None:
    """Identifica centros quirais com configuração R/S e mapeamento C1, C2..."""
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    centros = Chem.FindMolChiralCenters(mol, includeUnassigned=True)
    mapa_c = obter_mapa_carbonos(mol)

    resultado_centros = []
    for idx, config in centros:
        atomo = mol.GetAtomWithIdx(idx)
        rotulo_c = mapa_c.get(idx, f"Átomo {idx}")
        resultado_centros.append({
            "indice_rdkit": idx,
            "rotulo_carbono": rotulo_c,
            "elemento": atomo.GetSymbol(),
            "configuracao": config if config != "?" else "Não especificada (?)"
        })

    atividade_optica = classificar_atividade_optica(mol, centros)

    return {
        "centros": resultado_centros,
        "total_centros": len(resultado_centros),
        "atividade_optica": atividade_optica,
        "opticamente_ativo": atividade_optica == "Opticamente Ativa",
        "tem_centros": len(resultado_centros) > 0
    }


def gerar_estereoisomeros(smiles: str) -> list[str]:
    """Gera todas as combinações de estereoisômeros possíveis (2^n SMILES)."""
    if not validar_smiles(smiles):
        return []

    mol = Chem.MolFromSmiles(smiles.strip())
    opts = StereoEnumerationOptions(onlyUnassigned=False, unique=True)
    isomeros = list(EnumerateStereoisomers(mol, options=opts))

    return [Chem.MolToSmiles(iso, isomericSmiles=True) for iso in isomeros]


def contar_elementos_estereogenicos(smiles: str) -> int:
    """
    Retorna n, o número de elementos estereogênicos considerados por gerar_estereoisomeros
    (centros quirais, inclusive sem configuração definida, e ligações duplas E/Z).
    O máximo teórico de estereoisômeros é 2^n.
    """
    if not validar_smiles(smiles):
        return 0

    mol = Chem.MolFromSmiles(smiles.strip())
    # Mesmas opções de gerar_estereoisomeros; GetStereoisomerCount devolve 2^n
    opts = StereoEnumerationOptions(onlyUnassigned=False, unique=True)
    return GetStereoisomerCount(mol, options=opts).bit_length() - 1
