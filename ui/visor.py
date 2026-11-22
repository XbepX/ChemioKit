"""
Visor de estrutura com 2D e 3D: usado em todas as janelas que mostram moléculas.

janela(smiles, chave)        seletor 2D | 3D próprio + a estrutura
seletor_dimensao(chave)      só o seletor (para várias estruturas com um seletor comum)
visor(smiles, dim)           só a estrutura, na dimensão dada

O 3D é guardado em cache: a geometria é determinística (semente fixa) e o cálculo é o que mais
pesa, e o Streamlit refaz todas as abas a cada clique.
"""

import streamlit as st

from chemio_tools import gerar_html_3d, gerar_imagem_2d

from .estilo import ESCALA_ROTULOS

DIMENSOES = ["2D", "3D"]


@st.cache_data(show_spinner=False, max_entries=400)
def html_3d(smiles: str, mostrar_h: bool = False, destacar_quirais: bool = False, indices: tuple = (),
            rotulos: bool = False, hibridizacao: bool = False, altura: int = 300, estilo: str = "Ball & Stick",
            auto_spin: bool = False) -> str | None:
    return gerar_html_3d(smiles, estilo=estilo, mostrar_h=mostrar_h, destacar_quirais=destacar_quirais,
                         indices_destaque=list(indices), rotulos_carbonos=rotulos, rotulos_hibridizacao=hibridizacao,
                         auto_spin=auto_spin, largura="100%", altura=altura)


def seletor_dimensao(chave: str, padrao: str = "2D", rotulo: str = "Visualização") -> str:
    return st.segmented_control(rotulo, DIMENSOES, default=padrao, key=f"dim_{chave}", required=True,
                                label_visibility="collapsed") or padrao


def visor(smiles: str, dim: str, *, indices: list[int] | None = None, quirais: bool = False, rotulos: bool = False,
          hidrogenios: bool = False, hibridizacao: bool = False, altura_3d: int = 300, legenda: str | None = None):
    if dim == "3D":
        html = html_3d(smiles, mostrar_h=hidrogenios, destacar_quirais=quirais, indices=tuple(indices or ()),
                       rotulos=rotulos, hibridizacao=hibridizacao, altura=altura_3d)
        if html:
            st.iframe(html, height=altura_3d + 12)
        else:
            st.warning("Não foi possível calcular a geometria 3D.", icon="⚠️")
    else:
        imagem = gerar_imagem_2d(smiles, destacar_quirais=quirais, mostrar_indices=rotulos, mostrar_h=hidrogenios,
                                 colorir_hibridizacao=hibridizacao, indices_destaque_extra=indices,
                                 escala_rotulos=ESCALA_ROTULOS if (rotulos or quirais or hibridizacao) else None)
        if imagem is not None:
            st.image(imagem)
    if legenda:
        st.caption(legenda)


def janela(smiles: str, chave: str, padrao: str = "2D", **opcoes) -> str:
    """Estrutura com o próprio seletor 2D | 3D. Devolve a dimensão escolhida."""
    dim = seletor_dimensao(chave, padrao)
    visor(smiles, dim, **opcoes)
    return dim
