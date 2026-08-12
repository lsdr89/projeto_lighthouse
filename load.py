import csv
import os
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_DIR = "/home/leandro/projeto_lighthouse"

CSV_DIR = os.path.join(BASE_DIR, "csv")


# PostgreSQL Docker
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "lighthouse"
DB_USER = "postgres"
DB_PASSWORD = "postgres"


# Quantidade de registros enviados por lote
TAMANHO_LOTE = 1000


# ============================================================
# NORMALIZAÇÃO DOS NOMES
# ============================================================

def normalizar_nome(nome):

    nome = nome.strip().lower()

    for caractere in [" ", "-", ".", "/"]:
        nome = nome.replace(caractere, "_")

    return nome


# ============================================================
# NOME DA TABELA
# ============================================================

def nome_tabela(arquivo_csv):

    nome = os.path.splitext(arquivo_csv)[0]

    return normalizar_nome(nome)


# ============================================================
# CONEXÃO
# ============================================================

def conectar_banco():

    try:

        conexao = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        print(
            "Conexão com PostgreSQL realizada com sucesso."
        )

        return conexao

    except psycopg2.Error as erro:

        print()
        print("ERRO AO CONECTAR AO POSTGRESQL:")
        print(erro)

        return None


# ============================================================
# PREPARAÇÃO DA LINHA
# ============================================================

def preparar_linha(linha):

    """
    Mantém os valores do CSV como texto.

    Somente campos vazios são transformados em None,
    que o psycopg2 envia para o PostgreSQL como NULL.

    Não fazemos conversão de:
        CPF
        CNPJ
        telefone
        CEP
        IDs
        valores numéricos

    Isso preserva os dados originais do CSV.
    """

    return tuple(
        None if valor == "" else valor
        for valor in linha
    )


# ============================================================
# CARREGAMENTO DE UM CSV
# ============================================================

def carregar_csv(conexao, caminho_csv):

    arquivo = os.path.basename(caminho_csv)

    tabela = nome_tabela(arquivo)

    print()
    print("=" * 60)
    print(f"Arquivo: {arquivo}")
    print(f"Tabela:  {tabela}")
    print("=" * 60)

    cursor = conexao.cursor()

    try:

        # ----------------------------------------------------
        # Abre CSV
        # ----------------------------------------------------

        with open(
            caminho_csv,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as csv_file:

            leitor = csv.reader(csv_file)

            # ------------------------------------------------
            # Cabeçalho
            # ------------------------------------------------

            try:

                cabecalho = next(leitor)

            except StopIteration:

                print("CSV vazio. Ignorado.")

                return

            colunas = [
                normalizar_nome(coluna)
                for coluna in cabecalho
            ]

            # ------------------------------------------------
            # Mostra informações
            # ------------------------------------------------

            print()
            print("Colunas:")

            for coluna in colunas:
                print(f"  - {coluna}")

            # ------------------------------------------------
            # Cria SQL usando psycopg2.sql
            # ------------------------------------------------

            tabela_sql = sql.Identifier(tabela)

            colunas_sql = sql.SQL(", ").join(
                sql.Identifier(coluna)
                for coluna in colunas
            )

            comando = sql.SQL(
                "INSERT INTO {} ({}) VALUES %s"
            ).format(
                tabela_sql,
                colunas_sql
            )

            # ------------------------------------------------
            # Carregamento em lotes
            # ------------------------------------------------

            lote = []

            registros = 0

            primeiro_registro = True

            for linha in leitor:

                # --------------------------------------------
                # Verifica quantidade de colunas
                # --------------------------------------------

                if len(linha) != len(colunas):

                    raise ValueError(
                        f"O arquivo {arquivo} possui uma "
                        f"linha com {len(linha)} campos, "
                        f"mas o cabeçalho possui "
                        f"{len(colunas)} colunas."
                    )

                # --------------------------------------------
                # Prepara valores
                # --------------------------------------------

                linha_preparada = preparar_linha(
                    linha
                )

                # --------------------------------------------
                # Mostra primeiro registro
                # --------------------------------------------

                if primeiro_registro:

                    print()
                    print("Primeiro registro:")

                    for coluna, valor in zip(
                        colunas,
                        linha_preparada
                    ):

                        print(
                            f"  {coluna}: {valor}"
                        )

                    primeiro_registro = False

                lote.append(
                    linha_preparada
                )

                registros += 1

                # --------------------------------------------
                # Envia lote
                # --------------------------------------------

                if len(lote) >= TAMANHO_LOTE:

                    execute_values(
                        cursor,
                        comando.as_string(conexao),
                        lote
                    )

                    lote.clear()

                    print(
                        f"Registros carregados: "
                        f"{registros}"
                    )

            # ------------------------------------------------
            # Último lote
            # ------------------------------------------------

            if lote:

                execute_values(
                    cursor,
                    comando.as_string(conexao),
                    lote
                )

            # ------------------------------------------------
            # Commit
            # ------------------------------------------------

            conexao.commit()

            print()
            print(
                f"Carregamento concluído: "
                f"{registros} registros."
            )

    except Exception as erro:

        conexao.rollback()

        print()
        print(
            f"Erro ao carregar {arquivo}:"
        )

        print(erro)

        raise

    finally:

        cursor.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("CARREGAMENTO DOS CSVs")
    print("=" * 60)

    print()
    print(
        f"Diretório: {CSV_DIR}"
    )

    # --------------------------------------------------------
    # Verifica diretório
    # --------------------------------------------------------

    if not os.path.exists(CSV_DIR):

        print()
        print(
            "ERRO: Diretório dos CSVs não encontrado."
        )

        print(CSV_DIR)

        return

    # --------------------------------------------------------
    # Localiza CSVs
    # --------------------------------------------------------

    arquivos_csv = sorted(
        arquivo
        for arquivo in os.listdir(CSV_DIR)
        if arquivo.lower().endswith(".csv")
    )

    if not arquivos_csv:

        print()
        print(
            "ERRO: Nenhum arquivo CSV encontrado."
        )

        return

    print()
    print(
        f"Arquivos encontrados: "
        f"{len(arquivos_csv)}"
    )

    # --------------------------------------------------------
    # Conecta
    # --------------------------------------------------------

    conexao = conectar_banco()

    if conexao is None:

        return

    # --------------------------------------------------------
    # Carrega todos os CSVs
    # --------------------------------------------------------

    try:

        for arquivo_csv in arquivos_csv:

            caminho_csv = os.path.join(
                CSV_DIR,
                arquivo_csv
            )

            carregar_csv(
                conexao,
                caminho_csv
            )

    except Exception:

        print()
        print(
            "O carregamento foi interrompido "
            "devido a um erro."
        )

    finally:

        conexao.close()

        print()
        print("=" * 60)
        print(
            "CONEXÃO COM O BANCO ENCERRADA"
        )
        print("=" * 60)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    main()
