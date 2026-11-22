"""Anéis e aromaticidade, esqueleto de Murcko e tautômeros (RDKit)."""

from rdkit import Chem, RDLogger
from rdkit.Chem import rdMolDescriptors
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold

from .utils import validar_smiles

LIMITE_TAUTOMEROS = 50


def analisar_aneis(smiles: str) -> dict | None:
    """
    Anéis da molécula (menor conjunto de anéis do RDKit) e quais são aromáticos.
    Um anel é aromático quando todas as suas ligações são aromáticas no modelo de
    aromaticidade do RDKit (regra de Hückel aplicada a anéis e sistemas fundidos).
    Devolve total, aromaticos, e para cada anel: tamanho, aromatico, heteroatomos e indices.
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    info = mol.GetRingInfo()
    aneis = []
    for atomos, ligacoes in zip(info.AtomRings(), info.BondRings()):
        aromatico = all(mol.GetBondWithIdx(b).GetIsAromatic() for b in ligacoes)
        hetero = sorted(mol.GetAtomWithIdx(a).GetSymbol() for a in atomos if mol.GetAtomWithIdx(a).GetSymbol() != "C")
        aneis.append(
            {
                "tamanho": len(atomos),
                "aromatico": aromatico,
                "heteroatomos": hetero,
                "indices": list(atomos),
            }
        )
    return {
        "total": rdMolDescriptors.CalcNumRings(mol),
        "aromaticos": sum(a["aromatico"] for a in aneis),
        "aneis": aneis,
    }


def obter_esqueleto_murcko(smiles: str) -> dict | None:
    """
    Esqueleto de Bemis-Murcko: os anéis e as cadeias que ligam os anéis, sem as cadeias
    laterais. "generico" troca todos os átomos por carbono e todas as ligações por simples.
    Moléculas sem anel não têm esqueleto (devolve strings vazias).
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    esqueleto = MurckoScaffold.GetScaffoldForMol(mol)
    if esqueleto.GetNumAtoms() == 0:
        return {"esqueleto": "", "generico": "", "tem_anel": False}
    generico = MurckoScaffold.MakeScaffoldGeneric(esqueleto)
    return {
        "esqueleto": Chem.MolToSmiles(esqueleto),
        "generico": Chem.MolToSmiles(generico),
        "tem_anel": True,
    }


def gerar_tautomeros(smiles: str, maximo: int = LIMITE_TAUTOMEROS) -> dict | None:
    """
    Formas tautoméricas enumeradas pelo TautomerEnumerator do RDKit (regras de
    deslocamento de H como ceto-enol, imina-enamina e lactama-lactima).
    Devolve o tautômero canônico do RDKit, a lista (canônico primeiro) e se a lista foi
    cortada no limite. O "canônico" é uma escolha de padronização, não necessariamente a
    forma predominante em solução.
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    enumerador = rdMolStandardize.TautomerEnumerator()
    enumerador.SetMaxTautomers(maximo)
    RDLogger.DisableLog("rdApp.*")  # o enumerador avisa no terminal quando atinge o limite
    try:
        resultado = enumerador.Enumerate(mol)
        canonico = Chem.MolToSmiles(enumerador.Canonicalize(mol))
        todos = sorted({Chem.MolToSmiles(t) for t in resultado})
        limite_atingido = resultado.status == rdMolStandardize.TautomerEnumeratorStatus.MaxTautomersReached
    finally:
        RDLogger.EnableLog("rdApp.*")

    if canonico in todos:
        todos.remove(canonico)
    return {
        "canonico": canonico,
        "tautomeros": [canonico] + todos,
        "total": len(todos) + 1,
        "limite_atingido": limite_atingido,
    }
