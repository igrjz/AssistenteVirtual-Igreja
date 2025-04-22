import sqlite3
from sqlite3 import Error

def criar_conexao():
    """Cria conexão com o banco de dados SQLite"""
    conn = None
    try:
        conn = sqlite3.connect('conhecimento.db')
        return conn
    except Error as e:
        print(e)
    return conn

def criar_tabela(conn):
    """Cria tabela de conhecimento se não existir"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conhecimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topico TEXT NOT NULL,
            informacao TEXT NOT NULL,
            fonte TEXT,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            results_count INTEGER,
            data_pesquisa TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

    except Error as e:
        print(e)

def inicializar_db():
    """Inicializa o banco de dados"""
    conn = criar_conexao()
    if conn is not None:
        criar_tabela(conn)
        conn.close()

def adicionar_informacao(topico, informacao, fonte=None):
    """Adiciona nova informação à base de conhecimento"""
    conn = criar_conexao()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO conhecimento (topico, informacao, fonte) VALUES (?, ?, ?)", 
                         (topico, informacao, fonte))

            conn.commit()
            return True
        except Error as e:
            print(e)
        finally:
            conn.close()
    return False

def buscar_informacao(topico=None):
    """Busca informações na base de conhecimento"""
    conn = criar_conexao()
    if conn is not None:
        try:
            cursor = conn.cursor()
            if topico:
                cursor.execute("SELECT topico, informacao FROM conhecimento WHERE topico LIKE ?", 
                             (f'%{topico}%',))
            else:
                cursor.execute("SELECT topico, informacao FROM conhecimento")
            return cursor.fetchall()
        except Error as e:
            print(e)
        finally:
            conn.close()
    return []

def registrar_pesquisa(query, results_count=0):
    """Registra uma pesquisa no histórico"""
    conn = criar_conexao()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO search_history (query, results_count) VALUES (?, ?)",
                         (query, results_count))
            conn.commit()
            return True
        except Error as e:
            print(e)
        finally:
            conn.close()
    return False

def listar_topicos():
    """Lista todos os tópicos distintos na base de conhecimento"""

    conn = criar_conexao()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT topico FROM conhecimento")
            return [item[0] for item in cursor.fetchall()]
        except Error as e:
            print(e)
        finally:
            conn.close()
    return []
