# Dados do PubChem usados na verificação

`pubchem.csv` contém as propriedades dos cinco registros da Tabela 1 do TCC, baixadas do PubChem em 20/11/2026 pelo endereço:

https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/5816,444305,447315,875,16628/property/MolecularFormula,MolecularWeight,TPSA,XLogP,IUPACName,IsomericSMILES,DefinedAtomStereoCount,UndefinedAtomStereoCount/CSV

| CID | Molécula |
|---|---|
| 5816 | Adrenalina |
| 444305 | Ácido L-tartárico |
| 447315 | Ácido meso-tartárico |
| 875 | Ácido tartárico sem estereoquímica definida |
| 16628 | cis-1,2-Dimetilciclo-hexano |

O PubChem devolve o SMILES isomérico na coluna `SMILES`. A comparação é feita por `testes/verificar_pubchem.py`.

Fonte: National Center for Biotechnology Information. PubChem. National Library of Medicine. https://pubchem.ncbi.nlm.nih.gov
