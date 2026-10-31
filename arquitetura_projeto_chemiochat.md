# Documentação da Estrutura do Projeto

## 1. Árvore de Arquivos
```text
📂 ./
    📄 .gitignore
    📄 app.py
    📄 arquitetura_projeto.md
    📄 documenta_projeto.py
    📄 packages.txt
    📄 pyproject.toml
    📄 README.md
    📄 requirements.txt
    📄 uv.lock
    📂 .vscode/
        📄 settings.json
    📂 chemio_tools/
        📄 core.py
        📄 formatters.py
        📄 io_handlers.py
        📄 properties.py
        📄 stereochemistry.py
        📄 utils.py
        📄 visualization.py
        📄 __init__.py
    📂 testes/
        📄 testes_core.ipynb
    📂 ui/
        📄 inputs.py
        📄 tab_exportes.py
        📄 tab_properties.py
        📄 tab_visualization.py
        📄 __init__.py
```

## 2. Código-Fonte e Estrutura dos Arquivos

### `.gitignore`
```
# Ambiente virtual Python
.venv/
venv/
ENV/

# Arquivos de cache e compilação
__pycache__/
*.pyc
.pytest_cache/

# Configurações locais do VS Code e ambiente
.vscode/
.env

# Armazenamento vetorial (RAG futuro)
.chroma_db/
```

### `app.py`
```py
import streamlit as st
from chemio_tools import validar_smiles
from ui import (
    renderizar_secao_entradas,
    renderizar_aba_visualizacao,
    renderizar_aba_propriedades,
    renderizar_aba_exportacao
)

# Configuração da página
st.set_page_config(page_title="ChemioChat", layout="wide")
st.title("🧪 ChemioChat - Laboratório de Testes")

# 1. Seção Superior (Entrada de SMILES, Histórico e Upload)
smiles_input = renderizar_secao_entradas()

if not smiles_input.strip():
    st.stop()

if not validar_smiles(smiles_input):
    st.error("SMILES inválido! Verifique a sintaxe química digitada.")
    st.stop()

st.success("SMILES válido! A estrutura foi reconhecida pelo RDKit.")
st.write(f"SMILES capturado: `{smiles_input}`")

# Reset de estados ao alterar o SMILES
if "ultimo_smiles" not in st.session_state or st.session_state.ultimo_smiles != smiles_input:
    st.session_state.ultimo_smiles = smiles_input
    st.session_state.exibir_estereo = False
    st.session_state.exibir_isomeros = False
    st.session_state.grupo_ativo = "Nenhum"

# 2. Estrutura de Abas
tab_vis, tab_props, tab_export = st.tabs([
    "👁️ Visualização & Análise Interativa",
    "📊 Propriedades & Composição",
    "💾 Exportar Estrutura"
])

# 3. Chamada dos Módulos da Pasta UI
with tab_vis:
    renderizar_aba_visualizacao(smiles_input)

with tab_props:
    renderizar_aba_propriedades(smiles_input)

with tab_export:
    renderizar_aba_exportacao(smiles_input)
```

### `arquitetura_projeto.md`
```md

```

### `documenta_projeto.py`
```py
import os
from pathlib import Path


def gerar_documentacao(diretorio_raiz=".", arquivo_saida="arquitetura_projeto.md"):
    raiz = Path(diretorio_raiz)

    # Ignora pastas de ambiente virtual, git e cache
    pastas_ignoradas = {".venv", ".git", "__pycache__", "data"}

    # Ignora arquivos binários, locks e notebooks na extração de texto (mas mantém na árvore)
    extensoes_ignoradas_texto = {".png", ".jpg", ".jpeg", ".lock", ".ipynb", ".pdf"}

    with open(arquivo_saida, "w", encoding="utf-8") as f:
        f.write("# Documentação da Estrutura do Projeto\n\n")

        # 1. Gera a Árvore do Projeto
        f.write("## 1. Árvore de Arquivos\n```text\n")
        for dirpath, dirnames, filenames in os.walk(raiz):
            # Modifica a lista in-place para o os.walk ignorar as pastas não desejadas
            dirnames[:] = [d for d in dirnames if d not in pastas_ignoradas]

            nivel = dirpath.replace(str(raiz), "").count(os.sep)
            indentacao = " " * 4 * nivel
            f.write(f"{indentacao}📂 {os.path.basename(dirpath)}/\n")

            sub_indentacao = " " * 4 * (nivel + 1)
            for arquivo in filenames:
                f.write(f"{sub_indentacao}📄 {arquivo}\n")
        f.write("```\n\n")

        # 2. Extrai o conteúdo dos arquivos essenciais
        f.write("## 2. Código-Fonte e Estrutura dos Arquivos\n\n")
        for dirpath, dirnames, filenames in os.walk(raiz):
            dirnames[:] = [d for d in dirnames if d not in pastas_ignoradas]

            for arquivo in filenames:
                caminho_arquivo = Path(dirpath) / arquivo
                extensao = caminho_arquivo.suffix

                if extensao not in extensoes_ignoradas_texto:
                    f.write(f"### `{caminho_arquivo.relative_to(raiz)}`\n")
                    f.write(f"```{extensao.replace('.', '')}\n")

                    try:
                        with open(
                            caminho_arquivo, "r", encoding="utf-8"
                        ) as arq_leitura:
                            conteudo = arq_leitura.read()
                            # Trunca arquivos muito grandes (como o dados.json) para não poluir o relatório
                            if len(conteudo) > 3000:
                                f.write(
                                    conteudo[:3000]
                                    + "\n\n... [Conteúdo truncado por ser muito longo]\n"
                                )
                            else:
                                f.write(conteudo)
                    except Exception as e:
                        f.write(f"Erro ao ler arquivo: {e}\n")

                    f.write("\n```\n\n")


if __name__ == "__main__":
    gerar_documentacao()
    print("✅ Relatório de arquitetura gerado com sucesso em 'arquitetura_projeto.md'")

```

### `packages.txt`
```txt
libxrender1
libxext6
libcairo2
libgl1
```

### `pyproject.toml`
```toml
[project]
name = "quimiolab"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
    "numpy<2",
    "pandas<3",
    "rdkit",
    "ollama",
    "streamlit",
    "ipykernel",
    "pubchempy>=1.0.5",
    "py3dmol>=2.5.4",
]

```

### `README.md`
```md
# 🧪 ChemioChat - Laboratório de Testes & Quimioinformática

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?style=for-the-badge&logo=streamlit)
![RDKit](https://img.shields.io/badge/RDKit-Cheminformatics-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

O **ChemioChat** é uma plataforma web interativa para renderização, análise estrutural, estereoquímica e cálculo de propriedades físico-químicas de moléculas. Desenvolvido para servir como laboratório de testes e ambiente base para integrações de inteligência artificial aplicadas à química.

---

## 🚀 Funcionalidades Principais

### 👁️ Visualização & Análise Interativa (2D / 3D)
* **Motor 2D (RDKit):** 
  * Rótulos configuráveis (hidrogênios explícitos, índices de carbonos $C_1, C_2...$, metilas).
  * Destacar centros quirais com notação de asteriscos ($*$) e configuração absoluta $(R/S)$.
  * Personalização de espessura de traço, tamanho de fonte e fundo escuro.
* **Motor 3D (py3Dmol):**
  * Estilos de renderização: *Ball & Stick*, *Wireframe*, *Stick* e *CPK*.
  * Superfícies eletrônicas: *Van der Waals (VDW)*, *Superfície Acessível ao Solvente (SAS)* e *Mapa Eletrostático (MEP)*.
  * Giro automático (*Auto-Spin*) e destaque espacial de centros quirais em malhas tridimensionais.

### 🧪 Mapeamento Dinâmico de Grupos Funcionais
* Identificação automática via SMARTS pattern matching para: **Fenol**, **Álcool**, **Ácido Carboxílico**, **Aldeído**, **Cetona**, **Amina**, **Éster**, **Éter** e **Amida**.
* **Painel Interativo:** Botões de seleção individual que destacam a subestrutura diretamente no desenho 2D.

### 🧬 Estereoquímica & Isomeria
* Verificação de **Atividade Óptica** e determinação de centros assimétricos.
* **Enumeração de Estereoisômeros ($2^n$):** Galeria visual com a geração de todas as combinações estereoespecíficas da molécula.

### 📊 Propriedades Físico-Químicas & I/O
* Cálculo instantâneo de **Fórmula Molecular**, **Massa Molecular ($g/mol$)**, **LogP (Lipofilicidade)** e **TPSA ($\text{Å}^2$)**.
* Estequiometria detalhada de cada elemento presente na estrutura.
* **Importação Flexível:** Suporte a arquivos `.mol`, `.sdf` e `.pdb` exportados de editores moleculares (ChemSketch, Avogadro).
* **Exportação 3D:** Download do bloco de coordenadas otimizado em formatos `.SDF` e `.PDB`.

---

## 🏗️ Arquitetura do Projeto

O projeto adota o princípio de **Separação de Responsabilidades (*Separation of Concerns*)**, mantendo o motor químico isolado da camada visual:

```text
ChemioChat/
├── app.py                 # Orquestrador principal (Streamlit)
├── chemio_tools/          # Motor Químico (Lógica de negócio e RDKit)
│   ├── io_handlers.py     # Leitura e conversão de formatos (.mol, .sdf, .pdb)
│   ├── properties.py      # Cálculos físico-químicos e mapeamento SMARTS
│   ├── stereochemistry.py # Análise de quiralidade e

... [Conteúdo truncado por ser muito longo]

```

### `requirements.txt`
```txt
# This file was autogenerated by uv via the following command:
#    uv export --format requirements-txt -o requirements.txt
altair==6.2.2 \
    --hash=sha256:94014f8ad8617c3cb163d1137359cd6db5ba134b9b46d93cfd8b609fd245a583 \
    --hash=sha256:a1ff9d9cfe81c75414641826312b9471780e19d39293ba0b012933f6b6cba0fe
    # via streamlit
annotated-types==0.8.0 \
    --hash=sha256:13b2beaad985e05e2d6407ee4c4f35590b11f8d693a258a561055cac8f64cab7 \
    --hash=sha256:f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0
    # via pydantic
anyio==4.14.2 \
    --hash=sha256:9f505dda5ac9f0c8309b5e8bd445a8c2bf7246f3ce950121e45ea15bc41d1494 \
    --hash=sha256:cfa139f3ed1a23ee8f88a145ddb5ac7605b8bbfd8592baacd7ce3d8bb4313c7f
    # via
    #   httpx
    #   starlette
    #   streamlit
appnope==0.1.4 ; sys_platform == 'darwin' \
    --hash=sha256:1de3860566df9caf38f01f86f65e0e13e379af54f9e4bee1e66b48f2efffd1ee \
    --hash=sha256:502575ee11cd7a28c0205f379b525beefebab9d161b7c964670864014ed7213c
    # via ipykernel
asttokens==3.0.2 \
    --hash=sha256:3ecdbd8f2cc195f53ccada3a613538bb5f9ef6f6869129f13e03c30a677b8fe2 \
    --hash=sha256:9da13157f5b28becde0bd374fc677dcd3c290614264eff096f167c469cd9f933
    # via stack-data
attrs==26.1.0 \
    --hash=sha256:c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309 \
    --hash=sha256:d03ceb89cb322a8fd706d4fb91940737b6642aa36998fe130a9bc96c985eff32
    # via
    #   jsonschema
    #   referencing
blinker==1.9.0 \
    --hash=sha256:b4ce2265a7abece45e7cc896e98dbebe6cead56bcf805a3d23136d145f5445bf \
    --hash=sha256:ba0efaa9080b619ff2f3459d1d500c57bddea4a6b424b60a91141db6fd2f08bc
    # via streamlit
certifi==2026.7.22 \
    --hash=sha256:62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775 \
    --hash=sha256:741e2c3b351ddf169a738da9f2c048608ff7f2c5cc02f1ebc6b118bb090d5d55
    # via
    #   httpcore
    #   httpx
    #   requests
cffi==2.1.1 ; implementation_name == 'pypy' \
    --hash=sha256:046bfc24911b37851ee1b51aab8bffe713d89c68c6a057b09484ce9fd5f69b4e \
    --hash=sha256:208f941bb9d18e768138677f0a6d2ce01f590df56043dda1df1535ac57c88517 \
    --hash=sha256:210019b6c7cf07f081b4c54635c8cf744377001350e29cc0f81c4377b4797735 \
    --hash=sha256:3143d81e29e1e20a9ce10901ec369012947876596f75a222235965f2b7ae832e \
    --hash=sha256:4a7c934f7360e8cd64fe9efadcbd10c7c6364f531e432b9a4bf5ccbc9e0e8b50 \
    --hash=sha256:68e62fe11f30d5ca8289242866f0a5291402d8529ca2178ab8afc5c9694ae890 \
    --hash=sha256:7bde5e4cc5c10140859842b9d383af292b22639a4dffb725314baf45968cef80 \
    --hash=sha256:811bd1e21d32de12efca32393a0ab3f5133b54fce9bd44b8bd77ab07da14bf6a \
    --hash=sha256:c1453022f490d2459a11819d83ad1d586e9ff65a12ac3e705ffebd46d3685dcf \
    --hash=sha256:c8c69575568085ba0b1b10c0249d779a214aea6f6522e949a0fc9fb0fcb449d0 \
    --hash=sha256:dd31f52ea1086513bb9df30f8fcee9b8918323ae067a3d5b78bc826a000712be \
    --hash=sha256:f53e442b08449d42821fa4a4fba000095af9f62742a500f978a9f557ec44339a \
    --hash=sha256:f81b3b8

... [Conteúdo truncado por ser muito longo]

```

### `.vscode\settings.json`
```json
{
}
```

### `chemio_tools\core.py`
```py
import math
import py3Dmol
from rdkit import Chem
from rdkit.Chem import AllChem, Draw, Descriptors, rdMolDescriptors
from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers, StereoEnumerationOptions

# Mapeamento de padrões SMARTS para grupos funcionais comuns
GRUPOS_SMARTS = {
    "Ácido Carboxílico": "[CX3](=O)[OX2H1]",
    "Aldeído": "[CX3H1](=O)",
    "Cetona": "[#6][CX3](=O)[#6]",
    "Álcool": "[OX2H1][CX4]",
    "Amina": "[NX3;!$(NC=O)]",
    "Éster": "[CX3](=O)[OX2H0][#6]",
    "Éter": "[OD2]([#6])[#6]",
    "Amida": "[CX3](=O)[NX3]"
}


def validar_smiles(smiles: str) -> bool:
    """Valida se a string SMILES é reconhecida pelo RDKit."""
    if not smiles or not smiles.strip():
        return False
    mol = Chem.MolFromSmiles(smiles.strip())
    return mol is not None


def obter_mapa_carbonos(mol: Chem.Mol) -> dict[int, str]:
    """Mapeia os índices dos átomos do RDKit para a numeração sequencial de Carbonos (C1, C2...)."""
    mapa = {}
    contador_c = 1
    for atom in mol.GetAtoms():
        if atom.GetSymbol() == "C":
            mapa[atom.GetIdx()] = f"C{contador_c}"
            contador_c += 1
    return mapa


def obter_propriedades_basicas(smiles: str) -> dict | None:
    """Calcula massa molecular, LogP, TPSA e contagem de elementos."""
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    mol_com_h = Chem.AddHs(mol)

    contagem_elementos = {}
    for atom in mol_com_h.GetAtoms():
        simbolo = atom.GetSymbol()
        contagem_elementos[simbolo] = contagem_elementos.get(simbolo, 0) + 1

    return {
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "massa_molecular": round(Descriptors.MolWt(mol), 2),
        "logp": round(Descriptors.MolLogP(mol), 2),
        "tpsa": round(Descriptors.TPSA(mol), 2),
        "contagem_elementos": contagem_elementos
    }


def identificar_centros_quirais(smiles: str) -> dict | None:
    """Identifica centros quirais alinhados à numeração C1, C2 e avalia atividade óptica."""
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

    is_opticamente_ativo = len(resultado_centros) > 0 and any(
        c["configuracao"] in ["R", "S"] for c in resultado_centros
    )

    return {
        "centros": resultado_centros,
        "total_centros": len(resultado_centros),
        "opticamente_ativo": is_opticamente_ativo,

... [Conteúdo truncado por ser muito longo]

```

### `chemio_tools\formatters.py`
```py

```

### `chemio_tools\io_handlers.py`
```py
import io
from rdkit import Chem
from rdkit.Chem import AllChem
from .utils import validar_smiles


def carregar_mol_de_texto(conteudo_texto: str, formato: str = "MOL") -> str | None:
    """
    Converte arquivos de texto (.mol, .sdf, .pdb) em string SMILES.
    Base para carregar estruturas salvas em editores de moléculas.
    """
    if not conteudo_texto:
        return None

    mol = None
    formato_upper = formato.upper()

    try:
        if formato_upper in ["MOL", "SDF"]:
            mol = Chem.MolFromMolBlock(conteudo_texto)
        elif formato_upper == "PDB":
            mol = Chem.MolFromPDBBlock(conteudo_texto)

        if mol:
            return Chem.MolToSmiles(mol)
    except Exception:
        return None

    return None


def exportar_bloco_3d(smiles: str, formato: str = "SDF") -> str | None:
    """Exporta a estrutura 3D minimizada em formato SDF ou PDB para uso em editores externos."""
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    mol_3d = Chem.AddHs(mol)

    if AllChem.EmbedMolecule(mol_3d, randomSeed=42) != 0:
        return None

    AllChem.MMFFOptimizeMolecule(mol_3d)

    formato_upper = formato.upper()
    if formato_upper == "SDF":
        return Chem.MolToMolBlock(mol_3d)
    elif formato_upper == "PDB":
        return Chem.MolToPDBBlock(mol_3d)

    return None

```

### `chemio_tools\properties.py`
```py
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
from .utils import validar_smiles

# Dicionário SMARTS de grupos funcionais de interesse
GRUPOS_SMARTS = {
    "Ácido Carboxílico": "[CX3](=O)[OX2H1]",
    "Aldeído": "[CX3H1](=O)",
    "Cetona": "[#6][CX3](=O)[#6]",
    "Fenol": "[OX2H1][c]",
    "Álcool": "[OX2H1][CX4]",
    "Amina": "[NX3;!$(NC=O)]",
    "Éster": "[CX3](=O)[OX2H0][#6]",
    "Éter": "[OD2]([#6])[#6]",
    "Amida": "[CX3](=O)[NX3]"
}


def obter_propriedades_basicas(smiles: str) -> dict | None:
    """Calcula massa molecular, LogP, TPSA e contagem atômica elementar."""
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())
    mol_com_h = Chem.AddHs(mol)

    contagem_elementos = {}
    for atom in mol_com_h.GetAtoms():
        simbolo = atom.GetSymbol()
        contagem_elementos[simbolo] = contagem_elementos.get(simbolo, 0) + 1

    return {
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "massa_molecular": round(Descriptors.MolWt(mol), 2),
        "logp": round(Descriptors.MolLogP(mol), 2),
        "tpsa": round(Descriptors.TPSA(mol), 2),
        "contagem_elementos": contagem_elementos
    }


def identificar_grupos_funcionais(smiles: str) -> list[dict]:
    """Varre a estrutura em busca de grupos funcionais via SMARTS e retorna os índices associados."""
    if not validar_smiles(smiles):
        return []

    mol = Chem.MolFromSmiles(smiles.strip())
    grupos_encontrados = []

    for nome_grupo, smarts in GRUPOS_SMARTS.items():
        patt = Chem.MolFromSmarts(smarts)
        if patt and mol.HasSubstructMatch(patt):
            matches = mol.GetSubstructMatches(patt)
            indices_unicos = list(set([idx for tuple_match in matches for idx in tuple_match]))
            grupos_encontrados.append({
                "grupo": nome_grupo,
                "indices": indices_unicos
            })

    return grupos_encontrados

```

### `chemio_tools\stereochemistry.py`
```py
from rdkit import Chem
from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers, StereoEnumerationOptions
from .utils import validar_smiles, obter_mapa_carbonos


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

    is_opticamente_ativo = len(resultado_centros) > 0 and any(
        c["configuracao"] in ["R", "S"] for c in resultado_centros
    )

    return {
        "centros": resultado_centros,
        "total_centros": len(resultado_centros),
        "opticamente_ativo": is_opticamente_ativo,
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

```

### `chemio_tools\utils.py`
```py
from rdkit import Chem


def validar_smiles(smiles: str) -> bool:
    """Valida se a string SMILES é reconhecida pelo RDKit."""
    if not smiles or not smiles.strip():
        return False
    mol = Chem.MolFromSmiles(smiles.strip())
    return mol is not None


def obter_mapa_carbonos(mol: Chem.Mol) -> dict[int, str]:
    """
    Mapeia os índices dos átomos do RDKit para a numeração sequencial de Carbonos (C1, C2...).
    Utiliza a topologia do grafo de leitura para garantir estabilidade e previsibilidade.
    """
    mapa = {}
    contador_c = 1
    for atom in mol.GetAtoms():
        if atom.GetSymbol() == "C":
            mapa[atom.GetIdx()] = f"C{contador_c}"
            contador_c += 1
    return mapa
```

### `chemio_tools\visualization.py`
```py
import py3Dmol
from rdkit import Chem
from rdkit.Chem import AllChem, Draw
from .utils import validar_smiles, obter_mapa_carbonos


def gerar_imagem_2d(
    smiles: str,
    mostrar_h: bool = False,
    destacar_quirais: bool = False,
    mostrar_indices: bool = False,
    mostrar_metilas: bool = False,
    espessura_linha: int = 2,
    tamanho_fonte: int = 12,
    fundo_escuro: bool = False,
    indices_destaque_extra: list[int] = None
):
    """Gera a imagem 2D customizada alinhada às opções e destaque de centros quirais."""
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())

    if mostrar_h:
        mol = Chem.AddHs(mol)

    mapa_c = obter_mapa_carbonos(mol)

    if mostrar_indices:
        for atom in mol.GetAtoms():
            idx = atom.GetIdx()
            if idx in mapa_c:
                atom.SetProp("atomNote", mapa_c[idx])

    highlight_atoms = set()

    if destacar_quirais:
        # Força a verificação de estereocentros mesmo sem estereoquímica explícita
        mol_estereo = Chem.Mol(mol)
        Chem.AssignStereochemistry(mol_estereo, cleanIt=True, force=True, flagPossibleStereoCenters=True)
        centros = Chem.FindMolChiralCenters(mol_estereo, includeUnassigned=True)

        for idx, config in centros:
            highlight_atoms.add(idx)
            atomo = mol.GetAtomWithIdx(idx)
            note_existente = atomo.GetProp("atomNote") if atomo.HasProp("atomNote") else ""

            simbolo_config = f"({config})" if config != "?" else ""
            if note_existente:
                rotulo = f"{note_existente} {simbolo_config}*".strip()
            else:
                rotulo = f"{simbolo_config}*".strip()

            atomo.SetProp("atomNote", rotulo)

    if indices_destaque_extra:
        for idx in indices_destaque_extra:
            highlight_atoms.add(idx)

    opts = Draw.MolDrawOptions()
    opts.bondLineWidth = espessura_linha
    opts.minFontSize = tamanho_fonte
    opts.maxFontSize = tamanho_fonte + 6
    opts.explicitMethyl = mostrar_metilas

    if fundo_escuro:
        opts.clearBackground = False
        opts.setBackgroundColor((0.15, 0.17, 0.22, 1.0))

    return Draw.MolToImage(
        mol,
        size=(500, 420),
        options=opts,
        highlightAtoms=list(highlight_atoms) if highlight_atoms else None
    )


def gerar_html_3d(
    smiles: str,
    estilo: str = "Ball & Stick",
    mostrar_h: bool = True,
    fundo_escuro: bool = False,
    superficie: str = "Nenhuma",
    coloracao_superficie: str = "Mapa Eletrostático (MEP)",
    opacidade_superficie: float = 0.5,
    auto_spin: bool = False,
    destacar_quirais: bool = False,
    espessura_3d: int = 4,
    esquema_cor: str = "Elemento (Jmol)",
    raio_malha_quiral: float = 1.2
) -> str | None:
    """Gera a visualização 3D interativa sincronizando os centros quirais com o modelo final."""
    if not validar_smiles(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles.strip())


... [Conteúdo truncado por ser muito longo]

```

### `chemio_tools\__init__.py`
```py
from .utils import validar_smiles, obter_mapa_carbonos
from .properties import obter_propriedades_basicas, identificar_grupos_funcionais
from .stereochemistry import identificar_centros_quirais, gerar_estereoisomeros
from .visualization import gerar_imagem_2d, gerar_html_3d
from .io_handlers import carregar_mol_de_texto, exportar_bloco_3d

__all__ = [
    "validar_smiles",
    "obter_mapa_carbonos",
    "obter_propriedades_basicas",
    "identificar_grupos_funcionais",
    "identificar_centros_quirais",
    "gerar_estereoisomeros",
    "gerar_imagem_2d",
    "gerar_html_3d",
    "carregar_mol_de_texto",
    "exportar_bloco_3d"
]
```

### `ui\inputs.py`
```py
import streamlit as st
from chemio_tools.io_handlers import carregar_mol_de_texto


def renderizar_secao_entradas() -> str:
    """Renderiza a barra de entrada SMILES, histórico e o carregador de arquivos."""
    SMILES_INICIAL = "O=C[C@H](O)[C@@H](O)[C@H](O)[C@H](O)CO"

    if "historico_smiles" not in st.session_state:
        st.session_state.historico_smiles = [
            SMILES_INICIAL,
            "CC(=O)O",
            "CCO",
            "c1ccccc1"
        ]

    col_input, col_hist = st.columns([3, 1])

    with col_hist:
        smiles_selecionado = st.selectbox(
            "📜 Histórico / Exemplos:",
            options=st.session_state.historico_smiles,
            index=0
        )

    with col_input:
        smiles_input = st.text_input(
            "Digite o SMILES da molécula:",
            value=smiles_selecionado
        )

    with st.expander("📂 Ou carregar arquivo de estrutura (.mol, .sdf, .pdb)"):
        arquivo_enviado = st.file_uploader(
            "Arraste o arquivo exportado (ChemSketch, Avogadro, etc.):",
            type=["mol", "sdf", "pdb"]
        )
        if arquivo_enviado is not None:
            conteudo_texto = arquivo_enviado.getvalue().decode("utf-8")
            extensao = arquivo_enviado.name.split(".")[-1].upper()

            smiles_extraido = carregar_mol_de_texto(conteudo_texto, formato=extensao)
            if smiles_extraido:
                smiles_input = smiles_extraido
                st.success(f"Estrutura importada do arquivo: `{arquivo_enviado.name}`")
            else:
                st.error("Não foi possível ler a estrutura deste arquivo.")

    if smiles_input and smiles_input not in st.session_state.historico_smiles:
        st.session_state.historico_smiles.insert(0, smiles_input)

    return smiles_input
```

### `ui\tab_exportes.py`
```py
import streamlit as st
from chemio_tools import exportar_bloco_3d


def renderizar_aba_exportacao(smiles_input: str):
    """Renderiza a Aba 3: Download de arquivos 3D (.sdf e .pdb)."""
    st.subheader("📁 Download de Coordenadas 3D para Editores")
    st.caption("Baixe a molécula otimizada para abrir em softwares como Avogadro, PyMOL ou ChemSketch.")

    c_sdf, c_pdb, _ = st.columns([1.2, 1.2, 2])

    with c_sdf:
        sdf_data = exportar_bloco_3d(smiles_input, formato="SDF")
        if sdf_data:
            st.download_button(
                label="⬇️ Baixar Bloco SDF (.sdf)",
                data=sdf_data,
                file_name="molecula_3d.sdf",
                mime="chemical/x-mdl-sdfile"
            )

    with c_pdb:
        pdb_data = exportar_bloco_3d(smiles_input, formato="PDB")
        if pdb_data:
            st.download_button(
                label="⬇️ Baixar Arquivo PDB (.pdb)",
                data=pdb_data,
                file_name="molecula_3d.pdb",
                mime="chemical/x-pdb"
            )
```

### `ui\tab_properties.py`
```py
import streamlit as st
from chemio_tools import obter_propriedades_basicas


def renderizar_aba_propriedades(smiles_input: str):
    """Renderiza a Aba 2: Propriedades físico-químicas e contagem atômica."""
    dados = obter_propriedades_basicas(smiles_input)

    if dados:
        st.subheader("Métricas Físico-Químicas")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Fórmula Molecular", dados["formula"])
        col2.metric("Massa Molecular", f"{dados['massa_molecular']} g/mol")
        col3.metric("LogP (Lipofilicidade)", dados["logp"])
        col4.metric("TPSA", f"{dados['tpsa']} Å²")

        st.divider()
        st.subheader("Contagem de Átomos (Com H Explícitos)")

        elementos = dados["contagem_elementos"]
        cols_elem = st.columns(len(elementos))
        for col, (simbolo, quantidade) in zip(cols_elem, elementos.items()):
            col.metric(label=f"Átomos de {simbolo}", value=quantidade)
```

### `ui\tab_visualization.py`
```py
import streamlit as st
import streamlit.components.v1 as components
from chemio_tools import (
    gerar_imagem_2d,
    gerar_html_3d,
    identificar_grupos_funcionais,
    identificar_centros_quirais,
    gerar_estereoisomeros
)


def renderizar_aba_visualizacao(smiles_input: str):
    """Renderiza a Aba 1: Painel visual 2D/3D, seleção de grupos e estereoquímica."""
    grupos_funcionais = identificar_grupos_funcionais(smiles_input)

    # Controle de sessão dos painéis inferiores
    if "exibir_estereo" not in st.session_state:
        st.session_state.exibir_estereo = False
    if "exibir_isomeros" not in st.session_state:
        st.session_state.exibir_isomeros = False
    if "grupo_ativo" not in st.session_state:
        st.session_state.grupo_ativo = "Nenhum"

    col_render, col_controles = st.columns([3, 1])

    # PAINEL LATERAL DE CONTROLES
    with col_controles:
        st.subheader("⚙️ Opções")
        modo_vis = st.radio("Dimensão:", ("2D", "3D"), horizontal=True)
        st.divider()

        indices_grupo_selecionado = []

        if modo_vis == "2D":
            with st.expander("🏷️ Átomos e Rótulos", expanded=True):
                opt_mostrar_h = st.checkbox("Hidrogênios explícitos", value=False)
                opt_destacar_q = st.checkbox("Destacar quirais (* e R/S)", value=False)
                opt_mostrar_idx = st.checkbox("Índices dos carbonos (C1, C2...)", value=True)
                opt_metilas = st.checkbox("Exibir metilas (-CH₃)", value=False)

            with st.expander("🧪 Grupos Funcionais Mapeados", expanded=True):
                if grupos_funcionais:
                    st.caption("Clique no grupo para destacar no desenho:")
                    
                    if st.button("⚪ Limpar Destaque", key="btn_limpar_grupo"):
                        st.session_state.grupo_ativo = "Nenhum"

                    for g in grupos_funcionais:
                        nome_g = g["grupo"]
                        rotulo_btn = f"📌 {nome_g}" if st.session_state.grupo_ativo == nome_g else f"🧪 {nome_g}"
                        
                        if st.button(rotulo_btn, key=f"btn_grupo_{nome_g}"):
                            st.session_state.grupo_ativo = nome_g

                    if st.session_state.grupo_ativo != "Nenhum":
                        for g in grupos_funcionais:
                            if g["grupo"] == st.session_state.grupo_ativo:
                                indices_grupo_selecionado = g["indices"]
                else:
                    st.caption("Nenhum grupo funcional mapeado.")

            with st.expander("🎨 Estilo e Traço", expanded=False):
                opt_espessura = st.slider("Espessura da linha", min_value=1, max_value=5, value=2)
                opt_fonte = st.slider("Tamanho do texto", min_value=8, max_value=20, value=12)
                opt_fundo_escuro_2d = st.checkbox("Fundo escuro", value=False)

        else:
            with st.expander("🧊 Geometria e Estilo", expanded=T

... [Conteúdo truncado por ser muito longo]

```

### `ui\__init__.py`
```py
from .inputs import renderizar_secao_entradas
from .tab_visualization import renderizar_aba_visualizacao
from .tab_properties import renderizar_aba_propriedades
from .tab_exportes import renderizar_aba_exportacao

__all__ = [
    "renderizar_secao_entradas",
    "renderizar_aba_visualizacao",
    "renderizar_aba_propriedades",
    "renderizar_aba_exportacao"
]
```

