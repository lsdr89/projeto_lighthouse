import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="lighthouse",
    user="postgres",
    password="postgres"
)

print("Conectado com sucesso!")
