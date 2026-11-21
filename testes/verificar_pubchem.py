"""
Reverificação da Tabela 1 e do Quadro 3 do TCC.

Uso (na raiz do repositório):
    uv run python testes/verificar_pubchem.py testes/dados_pubchem/pubchem.csv

Sem o argumento, o script verifica apenas o Quadro 3.

O CSV é o que o PubChem devolve para (ver testes/dados_pubchem/LEIAME.md):
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/5816,444305,447315,875,16628/property/MolecularFormula,MolecularWeight,TPSA,XLogP,IUPACName,IsomericSMILES,DefinedAtomStereoCount,UndefinedAtomStereoCount/CSV

Para cada registro:
  1. roda as funções do ChemioKit com o SMILES isomérico do PubChem;
  2. confere as configurações R/S por um segundo método do RDKit (rdCIPLabeler,
     implementação das regras CIP de 2013, independente da usada pelo ChemioKit);
  3. extrai os descritores R/S do nome IUPAC do registro e compara com os dois métodos.
"""

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite importar chemio_tools a partir de testes/

from rdkit import Chem
from rdkit.Chem import rdCIPLabeler

from chemio_tools import (
    contar_elementos_estereogenicos,
    gerar_estereoisomeros,
    identificar_centros_quirais,
    identificar_grupos_funcionais,
    obter_propriedades_basicas,
)


def cip_novo(smiles):
    mol = Chem.MolFromSmiles(smiles)
    rdCIPLabeler.AssignCIPLabels(mol)
    return sorted(a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode"))


def descritores_do_nome(nome):
    blocos = re.findall(r"\(([0-9RSa-z,\s]+)\)", nome)
    letras = []
    for b in blocos:
        letras += re.findall(r"\d*([RS])\b", b)
    return sorted(letras)


def verificar_registros(caminho_csv):
    print("== Tabela 1: registros do PubChem\n")
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            smi = r.get("IsomericSMILES") or r.get("SMILES")
            p = obter_propriedades_basicas(smi)
            q = identificar_centros_quirais(smi)
            cfg_ck = sorted(c["configuracao"] for c in q["centros"] if c["configuracao"] in ("R", "S"))
            print(f"CID {r['CID']}  {r['IUPACName']}")
            print(f"  SMILES PubChem: {smi}")
            print(f"  fórmula   ChemioKit {p['formula']:<10} PubChem {r['MolecularFormula']}")
            print(f"  massa     ChemioKit {p['massa_molecular']:<10} PubChem {r['MolecularWeight']}")
            print(f"  TPSA      ChemioKit {p['tpsa']:<10} PubChem {r['TPSA']}")
            print(f"  LogP      ChemioKit {p['logp']:<10} PubChem XLogP3 {r.get('XLogP', '')}")
            print(f"  centros   ChemioKit {q['total_centros']} "
                  f"(PubChem: {r['DefinedAtomStereoCount']} definidos, {r['UndefinedAtomStereoCount']} indefinidos)")
            print(f"  R/S       ChemioKit {cfg_ck}  rdCIPLabeler {cip_novo(smi)}  nome IUPAC {descritores_do_nome(r['IUPACName'])}")
            print(f"  atividade {q['atividade_optica']}")
            print(f"  isômeros  {len(gerar_estereoisomeros(smi))} únicos; 2^n = {2 ** contar_elementos_estereogenicos(smi)}\n")


QUADRO_3 = [
    ("Etanol", "CCO"), ("Fenol", "Oc1ccccc1"), ("Ácido acético", "CC(=O)O"), ("Etanal", "CC=O"),
    ("Propanona", "CC(C)=O"), ("Etilamina", "CCN"), ("Acetato de etila", "CCOC(C)=O"),
    ("Éter dietílico", "CCOCC"), ("Acetamida", "CC(N)=O"),
    ("Ácido acetilsalicílico", "CC(=O)Oc1ccccc1C(=O)O"), ("Paracetamol", "CC(=O)Nc1ccc(O)cc1"),
    ("Nitrobenzeno", "O=[N+]([O-])c1ccccc1"), ("Ácido fórmico", "OC=O"),
]


def verificar_quadro3():
    print("== Quadro 3: grupos funcionais\n")
    for nome, smi in QUADRO_3:
        grupos = [g["grupo"] for g in identificar_grupos_funcionais(smi)]
        print(f"  {nome:<24} {smi:<26} {', '.join(grupos) or 'Nenhum'}")


if __name__ == "__main__":
    verificar_quadro3()
    if len(sys.argv) > 1:
        print()
        verificar_registros(sys.argv[1])
