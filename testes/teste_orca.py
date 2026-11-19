"""
Teste de viabilidade: leitura de saídas do ORCA e conversão para o RDKit.

Este script NÃO faz parte do motor (chemio_tools) nem da interface (ui).
Ele verifica se resultados de química quântica calculados pelo ORCA podem
ser trazidos para o pipeline do ChemioKit, como previsto nos trabalhos futuros.

Para cada arquivo .out da pasta testes/dados_orca/:
  1. a biblioteca cclib interpreta a saída do ORCA;
  2. a geometria final é convertida em uma molécula do RDKit, que deduz as
     ligações a partir das distâncias interatômicas (rdDetermineBonds);
  3. são exibidos o SMILES obtido, a energia SCF final, as energias dos
     orbitais de fronteira (HOMO e LUMO), as cargas atômicas e o dipolo.

Como executar (na raiz do repositório):
    uv run --with "cclib @ git+https://github.com/cclib/cclib@a13e17c1721f2613bb773db08ef91e7b2878fd10" python testes/teste_orca.py

Observação sobre a versão do cclib: a versão 1.8.1 publicada no PyPI lê as
saídas do ORCA 5.0, mas falha com as do ORCA 6.0 deste conjunto. Por isso o
comando acima fixa uma versão do repositório do cclib (novembro de 2026) que
lê os quatro arquivos.

Origem dos arquivos de teste: ver testes/dados_orca/LEIAME.md.
"""

import logging
import sys
from pathlib import Path

import cclib
from cclib.parser.utils import convertor
from rdkit import Chem
from rdkit.Chem import rdDetermineBonds

PASTA_DADOS = Path(__file__).parent / "dados_orca"
TABELA = Chem.GetPeriodicTable()


def molecula_da_geometria_final(dados) -> Chem.Mol:
    """Converte a última geometria lida pelo cclib em uma molécula do RDKit."""
    simbolos = [TABELA.GetElementSymbol(int(z)) for z in dados.atomnos]
    linhas = [f"{s} {x:.6f} {y:.6f} {z:.6f}" for s, (x, y, z) in zip(simbolos, dados.atomcoords[-1])]
    bloco_xyz = f"{len(simbolos)}\n\n" + "\n".join(linhas)
    mol = Chem.MolFromXYZBlock(bloco_xyz)
    rdDetermineBonds.DetermineBonds(mol, charge=int(getattr(dados, "charge", 0)))
    return mol


def resumir(arquivo: Path) -> None:
    print(f"== {arquivo.name}")
    try:
        dados = cclib.io.ccread(str(arquivo))
    except Exception as erro:  # versões antigas do cclib podem falhar com o ORCA 6
        print(f"   não foi possível ler o arquivo ({type(erro).__name__})")
        return
    if dados is None or not hasattr(dados, "atomcoords"):
        print("   não foi possível ler o arquivo")
        return

    mol = molecula_da_geometria_final(dados)
    simbolos = [a.GetSymbol() for a in mol.GetAtoms()]
    print(f"   SMILES deduzido: {Chem.MolToSmiles(Chem.RemoveHs(mol))}")
    print(f"   geometrias no arquivo: {len(dados.atomcoords)}")

    if hasattr(dados, "scfenergies"):
        energia = convertor(dados.scfenergies[-1], "eV", "hartree")
        print(f"   energia SCF final: {energia:.6f} Eh")

    if hasattr(dados, "moenergies") and hasattr(dados, "homos"):
        homo = dados.homos[0]
        print(f"   HOMO: {dados.moenergies[0][homo]:.3f} eV | LUMO: {dados.moenergies[0][homo + 1]:.3f} eV")

    for tipo, cargas in getattr(dados, "atomcharges", {}).items():
        amostra = ", ".join(f"{s}{i}={q:+.3f}" for i, (s, q) in enumerate(zip(simbolos, cargas)) if i < 4)
        print(f"   cargas de {tipo}: {amostra} ...")

    if hasattr(dados, "moments") and len(dados.moments) > 1:
        dipolo = sum(c * c for c in dados.moments[1]) ** 0.5
        print(f"   momento de dipolo: {dipolo:.3f} D")


def main() -> None:
    logging.disable(logging.CRITICAL)  # silencia os avisos internos do cclib
    arquivos = sorted(PASTA_DADOS.glob("*.out"))
    if not arquivos:
        sys.exit(f"Nenhum arquivo .out encontrado em {PASTA_DADOS}")
    print(f"cclib {cclib.__version__}\n")
    for arquivo in arquivos:
        resumir(arquivo)


if __name__ == "__main__":
    main()
