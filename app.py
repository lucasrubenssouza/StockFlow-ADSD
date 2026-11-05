from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)
DB = "estoque.db"

def conectar():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def inicializar():
    with conectar() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS categoria(
            id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE)""")
        con.execute("""CREATE TABLE IF NOT EXISTS produto(
            id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL CHECK(preco >= 0),
            quantidade INTEGER NOT NULL DEFAULT 0 CHECK(quantidade >= 0),
            id_categoria INTEGER,
            FOREIGN KEY(id_categoria) REFERENCES categoria(id_categoria))""")
        con.execute("""CREATE TABLE IF NOT EXISTS movimentacao(
            id_movimento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            data TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(id_produto) REFERENCES produto(id_produto))""")

@app.route("/")
def index():
    busca = request.args.get("q", "").strip()
    with conectar() as con:
        sql = """SELECT p.id_produto, p.nome, p.preco, p.quantidade,
                 COALESCE(c.nome,'Sem categoria') AS categoria
                 FROM produto p LEFT JOIN categoria c
                 ON c.id_categoria = p.id_categoria"""
        params = ()
        if busca:
            sql += " WHERE p.nome LIKE ?"
            params = (f"%{busca}%",)
        sql += " ORDER BY p.nome"
        produtos = con.execute(sql, params).fetchall()
    return render_template("index.html", produtos=produtos, busca=busca)

@app.route("/produto/novo", methods=["GET", "POST"])
def novo_produto():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        categoria = request.form["categoria"].strip()
        quantidade = int(request.form["quantidade"])
        preco = float(request.form["preco"].replace(",", "."))
        if not nome or quantidade < 0 or preco < 0:
            return "Dados inválidos", 400
        with conectar() as con:
            con.execute("INSERT OR IGNORE INTO categoria(nome) VALUES (?)", (categoria,))
            cat = con.execute("SELECT id_categoria FROM categoria WHERE nome=?", (categoria,)).fetchone()
            con.execute("""INSERT INTO produto(nome, preco, quantidade, id_categoria)
                           VALUES (?, ?, ?, ?)""",
                        (nome, preco, quantidade, cat["id_categoria"]))
        return redirect("/")
    return render_template("novo.html")

@app.route("/produto/<int:id_produto>/quantidade", methods=["POST"])
def atualizar_quantidade(id_produto):
    nova = int(request.form["quantidade"])
    if nova < 0:
        return "Quantidade inválida", 400
    with conectar() as con:
        atual = con.execute("SELECT quantidade FROM produto WHERE id_produto=?",
                            (id_produto,)).fetchone()
        diferenca = nova - atual["quantidade"]
        con.execute("UPDATE produto SET quantidade=? WHERE id_produto=?",
                    (nova, id_produto))
        con.execute("""INSERT INTO movimentacao(id_produto, tipo, quantidade)
                       VALUES (?, 'AJUSTE', ?)""", (id_produto, diferenca))
    return redirect("/")

if __name__ == "__main__":
    inicializar()
    app.run(debug=True)
