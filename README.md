# 🧪 ChemioKit - Toolkit de Quimioinformática

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?style=for-the-badge&logo=streamlit)
![RDKit](https://img.shields.io/badge/RDKit-Cheminformatics-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

O **ChemioKit** é um toolkit de quimioinformática em Python, com interface web em Streamlit, para renderização, análise estrutural, estereoquímica e cálculo de propriedades físico-químicas de moléculas orgânicas. Toda a representação e todo o cálculo são delegados ao RDKit e ao py3Dmol, e as funções do motor químico foram organizadas para servir de ferramentas a um futuro agente conversacional de química, o **ChemioChat**.

---

## 🚀 Funcionalidades Principais

### 👁️ Visualização & Análise Interativa (2D / 3D)
* **Motor 2D (RDKit):** 
  * Rótulos configuráveis (hidrogênios explícitos, índices de carbonos $C_1, C_2...$, metilas).
  * Destacar centros quirais com notação de asteriscos ($*$) e configuração absoluta $(R/S)$.
  * Personalização de espessura de traço, tamanho de fonte e fundo escuro.
* **Motor 3D (py3Dmol):**
  * Estilos de renderização: *Ball & Stick*, *Wireframe*, *Stick* e *CPK*.
  * Superfícies eletrônicas: *Van der Waals (VDW)*, *Superfície Acessível ao Solvente (SAS)* e *coloração por cargas parciais de Gasteiger*.
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
ChemioKit/
├── app.py                 # Orquestrador principal (Streamlit)
├── chemio_tools/          # Motor Químico (Lógica de negócio e RDKit)
│   ├── io_handlers.py     # Leitura e conversão de formatos (.mol, .sdf, .pdb)
│   ├── properties.py      # Cálculos físico-químicos e mapeamento SMARTS
│   ├── stereochemistry.py # Análise de quiralidade e enumeração 2^n
│   ├── utils.py           # Validadores e mapeadores auxiliares
│   └── visualization.py   # Renderização gráfica 2D (RDKit) e 3D (py3Dmol)
├── ui/                    # Componentes da Interface Gráfica
│   ├── inputs.py          # Barra de entrada SMILES, histórico e file uploader
│   ├── tab_visualization.py # Aba 1: Renderização 2D/3D e controles
│   ├── tab_properties.py    # Aba 2: Tabela de métricas e composição
│   └── tab_exportes.py      # Aba 3: Painel de downloads
├── testes/                # Testes unitários do motor químico
├── pyproject.toml         # Configuração de dependências
└── README.md
```

---

## ⚙️ Instalação e uso

Requer Python 3.12 e o gerenciador [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/XbepX/ChemioKit.git
cd ChemioKit
uv sync
uv run streamlit run app.py
```

---

## 🧭 Próximas etapas: ChemioChat

O ChemioKit é a camada de ferramentas de um projeto maior: o **ChemioChat**, um agente conversacional de química que acionará as funções do motor químico por *tool calling*. Nessa arquitetura, o modelo de linguagem interpreta o pedido do estudante e escolhe a função adequada, enquanto toda a representação e o cálculo continuam sendo feitos de forma determinística pelo RDKit e pelo py3Dmol.

---

## 📄 Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).
