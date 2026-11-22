"""Comparação de duas moléculas: similaridade de Tanimoto e maior subestrutura comum (MCS)."""

from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator, rdFMCS

from .utils import validar_smiles

TEMPO_LIMITE_MCS = 10  # segundos; a busca da MCS pode demorar em moléculas grandes

_gerador_morgan = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


def comparar_moleculas(smiles_a: str, smiles_b: str) -> dict | None:
    """
    - tanimoto: similaridade de 0 a 1 entre impressões digitais de Morgan (raio 2, 2048 bits),
      o padrão mais usado em quimioinformática (equivalente ao ECFP4);
    - mcs: maior subestrutura comum (rdFMCS), com o SMARTS, o número de átomos e ligações e
      os índices dos átomos em cada molécula, para destacar no desenho. Anéis só casam com
      anéis inteiros, para a subestrutura fazer sentido químico.
    "mcs.completa" é False se a busca parou no tempo limite (o resultado pode ser menor que o real).
    """
    if not (validar_smiles(smiles_a) and validar_smiles(smiles_b)):
        return None

    mol_a = Chem.MolFromSmiles(smiles_a.strip())
    mol_b = Chem.MolFromSmiles(smiles_b.strip())

    tanimoto = DataStructs.TanimotoSimilarity(
        _gerador_morgan.GetFingerprint(mol_a), _gerador_morgan.GetFingerprint(mol_b)
    )

    resultado = rdFMCS.FindMCS(
        [mol_a, mol_b],
        timeout=TEMPO_LIMITE_MCS,
        ringMatchesRingOnly=True,
        completeRingsOnly=True,
    )
    indices_a: list[int] = []
    indices_b: list[int] = []
    if resultado.numAtoms > 0:
        consulta = Chem.MolFromSmarts(resultado.smartsString)
        indices_a = list(mol_a.GetSubstructMatch(consulta))
        indices_b = list(mol_b.GetSubstructMatch(consulta))

    return {
        "tanimoto": round(tanimoto, 3),
        "identicas": Chem.MolToSmiles(mol_a) == Chem.MolToSmiles(mol_b),
        "mcs": {
            "smarts": resultado.smartsString,
            "num_atomos": resultado.numAtoms,
            "num_ligacoes": resultado.numBonds,
            "completa": not resultado.canceled,
            "indices_a": indices_a,
            "indices_b": indices_b,
        },
    }
