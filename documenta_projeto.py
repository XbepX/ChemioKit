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
