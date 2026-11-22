"""
Hibridização dos carbonos e contagem de ligações sigma (σ) e pi (π).

Regras de contagem (todas as ligações, inclusive as com hidrogênio):
  simples = 1σ;  dupla = 1σ + 1π;  tripla = 1σ + 2π.
Anéis aromáticos são kekulizados antes da contagem (o benzeno vira 3 simples e 3
duplas alternadas), que é a representação usada no ensino médio.
"""

from rdkit import Chem

from .utils import obter_mapa_carbonos, validar_smiles

_HIBRIDIZACAO = {
    Chem.HybridizationType.SP3: "sp3",
    Chem.HybridizationType.SP2: "sp2",
    Chem.HybridizationType.SP: "sp",
}


def analisar_hibridizacao_e_ligacoes(smiles: str) -> dict | None:
    """
    Devolve:
      carbonos: [{indice_rdkit, rotulo_carbono (C1, C2...), hibridizacao ("sp3" | "sp2" | "sp")}]
      contagem_hibridizacao: {"sp3": n, "sp2": n, "sp": n}
      ligacoes: {"simples": n, "duplas": n, "triplas": n}   (após kekulizar e com H explícitos)
      sigma, pi: totais
    Carbonos com hibridização fora dessas três (raro: ex. carbono isolado) aparecem com
    o nome dado pelo RDKit e não entram na contagem_hibridizacao.
    """
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    mapa_c = obter_mapa_carbonos(mol)

    carbonos = []
    contagem = {"sp3": 0, "sp2": 0, "sp": 0}
    for atomo in mol.GetAtoms():
        if atomo.GetSymbol() != "C":
            continue
        hib = _HIBRIDIZACAO.get(atomo.GetHybridization(), str(atomo.GetHybridization()))
        if hib in contagem:
            contagem[hib] += 1
        carbonos.append(
            {"indice_rdkit": atomo.GetIdx(), "rotulo_carbono": mapa_c[atomo.GetIdx()], "hibridizacao": hib}
        )

    mol_h = Chem.AddHs(mol)
    Chem.Kekulize(mol_h, clearAromaticFlags=True)

    ligacoes = {"simples": 0, "duplas": 0, "triplas": 0}
    sigma = pi = 0
    for ligacao in mol_h.GetBonds():
        tipo = ligacao.GetBondType()
        if tipo == Chem.BondType.SINGLE:
            ligacoes["simples"] += 1
            sigma += 1
        elif tipo == Chem.BondType.DOUBLE:
            ligacoes["duplas"] += 1
            sigma += 1
            pi += 1
        elif tipo == Chem.BondType.TRIPLE:
            ligacoes["triplas"] += 1
            sigma += 1
            pi += 2

    return {
        "carbonos": carbonos,
        "contagem_hibridizacao": contagem,
        "ligacoes": ligacoes,
        "sigma": sigma,
        "pi": pi,
    }
