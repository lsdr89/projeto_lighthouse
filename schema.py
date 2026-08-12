import csv
import os
from datetime import datetime


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_DIR = "/home/leandro/projeto_lighthouse"

CSV_DIR = os.path.join(BASE_DIR, "csv")

OUTPUT_FILE = os.path.join(BASE_DIR, "schema.sql")


# ============================================================
# COLUNAS QUE REPRESENTAM IDENTIFICADORES
# ============================================================
#
# Esses campos devem ser TEXT mesmo quando possuem
# somente números.
#
# Motivo:
# CPF, CNPJ, telefone, CEP etc. são identificadores
# e não valores utilizados para cálculos.
# ============================================================

COLUNAS_TEXT = {
    "cpf",
    "cnpj",
    "tax_id",
    "document",
    "document_id",
    "document_number",
    "documento",

    "phone",
    "telephone",
    "mobile",
    "cellphone",
    "telefone",
    "celular",

    "zip",
    "zipcode",
    "postal_code",
    "cep",

    "state_registration",
    "inscricao_estadual",

    "email",
}


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_nome(nome):

    nome = nome.strip().lower()

    for caractere in [" ", "-", ".", "/"]:

        nome = nome.replace(
            caractere,
            "_"
        )

    return nome


# ============================================================
# VERIFICA SE A COLUNA DEVE SER TEXT
# ============================================================

def coluna_deve_ser_text(coluna):

    coluna = normalizar_nome(coluna)

    # Correspondência exata
    if coluna in COLUNAS_TEXT:
        return True

    # Regras adicionais
    palavras_text = [
        "cpf",
        "cnpj",
        "tax_id",
        "document",
        "phone",
        "telephone",
        "mobile",
        "cellphone",
        "telefone",
        "celular",
        "zipcode",
        "postal_code",
        "cep",
        "state_registration",
        "inscricao_estadual",
        "email"
    ]

    for palavra in palavras_text:

        if palavra in coluna:
            return True

    return False


# ============================================================
# DETECÇÃO DE TIPO
# ============================================================

def detectar_tipo(valor):

    if valor is None:
        return "TEXT"

    valor = valor.strip()

    if valor == "":
        return "TEXT"

    # BOOLEAN
    if valor.lower() in ("true", "false"):
        return "BOOLEAN"

    # INTEGER
    try:

        numero = int(valor)

        # PostgreSQL INTEGER:
        # -2147483648 até 2147483647
        if -2147483648 <= numero <= 2147483647:
            return "INTEGER"

        # Números maiores que INTEGER
        # serão BIGINT
        if -9223372036854775808 <= numero <= 9223372036854775807:
            return "BIGINT"

        return "NUMERIC"

    except ValueError:
        pass

    # NUMERIC
    try:

        float(valor)

        return "NUMERIC"

    except ValueError:
        pass

    # DATAS / TIMESTAMP
    formatos = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f"
    ]

    for formato in formatos:

        try:

            datetime.strptime(
                valor,
                formato
            )

            if "H" in formato:
                return "TIMESTAMP"

            return "DATE"

        except ValueError:
            pass

    # Texto
    return "TEXT"


# ============================================================
# DETECTA TIPOS DAS COLUNAS
# ============================================================

def detectar_tipos(caminho_csv):

    with open(
        caminho_csv,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as arquivo:

        leitor = csv.DictReader(arquivo)

        colunas_originais = leitor.fieldnames

        if not colunas_originais:
            return [], {}

        colunas = [
            normalizar_nome(coluna)
            for coluna in colunas_originais
        ]

        valores = {
            coluna: []
            for coluna in colunas
        }

        # Analisa até 100 valores por coluna
        for linha in leitor:

            for original, normalizada in zip(
                colunas_originais,
                colunas
            ):

                valor = linha.get(original)

                if (
                    valor is not None
                    and valor != ""
                    and len(valores[normalizada]) < 100
                ):

                    valores[normalizada].append(
                        valor
                    )

    tipos = {}

    for coluna in colunas:

        # ====================================================
        # IDENTIFICADORES SEMPRE TEXT
        # ====================================================

        if coluna_deve_ser_text(coluna):

            tipos[coluna] = "TEXT"

            continue

        # ====================================================
        # SEM VALORES
        # ====================================================

        if not valores[coluna]:

            tipos[coluna] = "TEXT"

            continue

        # ====================================================
        # DETECÇÃO
        # ====================================================

        tipos_detectados = [
            detectar_tipo(valor)
            for valor in valores[coluna]
        ]

        # ====================================================
        # MESMO TIPO
        # ====================================================

        primeiro_tipo = tipos_detectados[0]

        if all(
            tipo == primeiro_tipo
            for tipo in tipos_detectados
        ):

            tipos[coluna] = primeiro_tipo

        else:

            # Se houver mistura de tipos,
            # usa TEXT para evitar perda de dados.
            tipos[coluna] = "TEXT"

    return colunas, tipos


# ============================================================
# NOME DA TABELA
# ============================================================

def nome_tabela(arquivo):

    nome = os.path.splitext(
        arquivo
    )[0]

    return normalizar_nome(nome)


# ============================================================
# GERA CREATE TABLE
# ============================================================

def gerar_create_table(
    tabela,
    colunas,
    tipos
):

    linhas = []

    for coluna in colunas:

        linhas.append(
            f'    "{coluna}" {tipos[coluna]}'
        )

    sql = (
        f'CREATE TABLE "{tabela}" (\n'
    )

    sql += ",\n".join(linhas)

    sql += "\n);\n"

    return sql


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("GERADOR DE SCHEMA POSTGRESQL")
    print("=" * 60)

    if not os.path.exists(CSV_DIR):

        print(
            f"Diretório não encontrado: {CSV_DIR}"
        )

        return

    arquivos = sorted(
        arquivo
        for arquivo in os.listdir(CSV_DIR)
        if arquivo.lower().endswith(".csv")
    )

    if not arquivos:

        print("Nenhum CSV encontrado.")

        return

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as arquivo_sql:

        arquivo_sql.write(
            "-- Schema gerado automaticamente\n"
        )

        arquivo_sql.write(
            "-- PostgreSQL\n\n"
        )

        for arquivo in arquivos:

            caminho = os.path.join(
                CSV_DIR,
                arquivo
            )

            tabela = nome_tabela(
                arquivo
            )

            print(
                f"Processando: {arquivo}"
            )

            colunas, tipos = detectar_tipos(
                caminho
            )

            sql = gerar_create_table(
                tabela,
                colunas,
                tipos
            )

            arquivo_sql.write(
                f"-- Tabela: {tabela}\n"
            )

            arquivo_sql.write(sql)
            arquivo_sql.write("\n")

            # Mostra os tipos detectados
            if tabela == "customers":

                print()
                print(
                    "Tipos detectados em customers:"
                )

                for coluna in colunas:

                    print(
                        f"  {coluna}: "
                        f"{tipos[coluna]}"
                    )

                print()

    print()
    print("=" * 60)
    print("SCHEMA GERADO")
    print("=" * 60)
    print()
    print(OUTPUT_FILE)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()
