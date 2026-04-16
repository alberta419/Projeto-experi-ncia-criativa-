from fastapi import FastAPI, Form, Depends
from fastapi.responses import JSONResponse
import pymysql

app = FastAPI()

def get_db():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="12345",
        database="petshop"
    )

# LOGIN
@app.post("/login")
def login(email: str = Form(...), senha: str = Form(...), db=Depends(get_db)):
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(
            "SELECT * FROM admin WHERE email=%s AND senha=%s",
            (email, senha)
        )
        user = cursor.fetchone()

    if user:
        return {"status": "ok"}
    return JSONResponse(status_code=401, content={"status": "erro"})

#PETS 
@app.get("/pets")
def listar_pets(db=Depends(get_db)):
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM pets")
        return cursor.fetchall()

@app.post("/pets")
def add_pet(nome: str = Form(...), nascimento: str = Form(...),
            especie: str = Form(...), raca: str = Form(...),
            db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO pets (nome,nascimento,especie,raca) VALUES (%s,%s,%s,%s)",
            (nome, nascimento, especie, raca)
        )
        db.commit()
    return {"msg": "ok"}

#EVENTOS
@app.get("/eventos")
def listar_eventos(db=Depends(get_db)):
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT e.*, p.nome as pet_nome 
            FROM eventos e
            JOIN pets p ON e.pet_id = p.id
        """)
        return cursor.fetchall()

@app.post("/eventos")
def add_evento(pet_id: int = Form(...), data: str = Form(...),
               hora: str = Form(...), tipo: str = Form(...),
               descricao: str = Form(...), local: str = Form(...),
               observacoes: str = Form(...), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO eventos 
            (pet_id,data,hora,tipo,descricao,local,observacoes)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (pet_id, data, hora, tipo, descricao, local, observacoes))
        db.commit()
    return {"msg": "ok"}

#FUNCIONARIOS
@app.get("/funcionarios")
def listar_funcionarios(db=Depends(get_db)):
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM funcionarios")
        return cursor.fetchall()


@app.post("/funcionarios")
def add_funcionario(
    nome: str = Form(...),
    cargo: str = Form(...),
    salario: float = Form(...),
    telefone: str = Form(...),
    db=Depends(get_db)
):
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO funcionarios (nome, cargo, salario, telefone) VALUES (%s,%s,%s,%s)",
            (nome, cargo, salario, telefone)
        )
        db.commit()

    return {"msg": "Funcionário cadastrado"}


@app.delete("/funcionarios/{id}")
def deletar_funcionario(id: int, db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM funcionarios WHERE id=%s", (id,))
        db.commit()

    return {"msg": "Funcionário removido"}


@app.put("/funcionarios/{id}")
def atualizar_funcionario(
    id: int,
    nome: str = Form(...),
    cargo: str = Form(...),
    salario: float = Form(...),
    telefone: str = Form(...),
    db=Depends(get_db)
):
    with db.cursor() as cursor:
        cursor.execute(
            "UPDATE funcionarios SET nome=%s, cargo=%s, salario=%s, telefone=%s WHERE id=%s",
            (nome, cargo, salario, telefone, id)
        )
        db.commit()

    return {"msg": "Funcionário atualizado"}