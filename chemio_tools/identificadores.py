"""Identificadores da estrutura: SMILES canônico, InChI e InChIKey (RDKit)."""

from rdkit import Chem, RDLogger

from .utils import validar_smiles


def obter_identificadores(smiles: str) -> dict | None:
    """
    SMILES canônico (com estereoquímica, quando houver), InChI padrão e InChIKey.
    O InChIKey é um "resumo" de 27 caracteres do InChI, usado para buscar a estrutura
    em bancos de dados como o PubChem.
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    RDLogger.DisableLog("rdApp.*")  # o gerador de InChI escreve avisos no terminal
    try:
        inchi = Chem.MolToInchi(mol)
        inchikey = Chem.InchiToInchiKey(inchi) if inchi else ""
    finally:
        RDLogger.EnableLog("rdApp.*")

    return {
        "smiles_canonico": Chem.MolToSmiles(mol),
        "inchi": inchi or None,
        "inchikey": inchikey or None,
    }
