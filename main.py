from fastapi import FastAPI, Form, Depends, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mysql.connector
import hashlib
from datetime import date, datetime
import shutil
from pathlib import Path

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")

def hash_senha(senha: str) -> str:
    """Transforma a senha em um código SHA-256 irreversível"""
    return hashlib.sha256(senha.encode()).hexdigest()

def calcular_idade(nascimento):
    if not nascimento:
        return "N/A"
    if isinstance(nascimento, str):
        try:
            nascimento = datetime.strptime(nascimento, '%Y-%m-%d').date()
        except ValueError:
            return "N/A"
    
    hoje = date.today()
    anos = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
    if anos == 0:
        meses = (hoje.year - nascimento.year) * 12 + hoje.month - nascimento.month
        return f"{meses} meses"
    return f"{anos} anos"

def setup_database(conn):
    """Executa a configuração inicial do banco de dados (criação de tabelas, etc)."""
    # Garante que a tabela clientes exista automaticamente!
    cursor = conn.cursor(buffered=True)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            cpf VARCHAR(20) NOT NULL,
            nascimento VARCHAR(15) NOT NULL,
            telefone VARCHAR(20) NOT NULL,
            senha VARCHAR(100) NOT NULL
        )
    """)

    # Garante que a tabela clientes tenha a coluna de foto de perfil
    try:
        cursor.execute("ALTER TABLE clientes ADD COLUMN profile_pic_url VARCHAR(255) DEFAULT '/assets/img/default-profile.png'")
    except mysql.connector.Error:
        pass # Coluna já existe
    

    # Garante que a tabela pets tenha a coluna cliente_id para vincular o pet ao dono
    try:
        cursor.execute("ALTER TABLE pets ADD COLUMN cliente_id INT")
    except mysql.connector.Error:
        pass # Se der erro, é porque a coluna já existe
    

    # Garante que a tabela pets tenha as novas colunas de medidas
    try:
        cursor.execute("ALTER TABLE pets ADD COLUMN peso DECIMAL(5,2), ADD COLUMN altura DECIMAL(5,2), ADD COLUMN comprimento DECIMAL(5,2), ADD COLUMN largura DECIMAL(5,2)")
    except mysql.connector.Error:
        pass
    

    # Tabelas Administrativas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) UNIQUE NOT NULL,
            senha VARCHAR(100) NOT NULL
        )
    """)
    # Garante que a tabela admin tenha as colunas de nome e foto de perfil
    try:
        cursor.execute("ALTER TABLE admin ADD COLUMN nome VARCHAR(100) NOT NULL DEFAULT 'Admin'")
    except mysql.connector.Error:
        pass # Coluna já existe
    try:
        cursor.execute("ALTER TABLE admin ADD COLUMN profile_pic_url VARCHAR(255) DEFAULT '/assets/img/default-profile.png'")
    except mysql.connector.Error:
        pass # Coluna já existe

    # Cria um admin padrão caso não exista nenhum
    cursor.execute("SELECT * FROM admin WHERE email='admin@gmail.com'")
    if not cursor.fetchone():
        senha_admin = hash_senha('123456')
        cursor.execute("INSERT INTO admin (email, senha, nome) VALUES ('admin@gmail.com', %s, 'Administrador')", (senha_admin,))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cargos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            cargo VARCHAR(100) NOT NULL,
            salario DECIMAL(10,2) NOT NULL,
            telefone VARCHAR(20) NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    

def get_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="petshop"
    )
    return conn

# Bloco para configurar o banco de dados na inicialização do app.
# Isso evita que a verificação de tabelas ocorra em cada request.
def run_db_setup():
    print("Iniciando verificação do banco de dados...")
    try:
        db_conn = get_db()
        setup_database(db_conn)
        db_conn.close()
        print("Verificação do banco de dados concluída com sucesso.")
    except Exception as e:
        print(f"Erro ao configurar o banco de dados na inicialização: {e}")

run_db_setup()

async def get_current_user(request: Request, db: mysql.connector.connection.MySQLConnection = Depends(get_db)):
    """Dependência para obter o usuário (cliente ou admin) logado a partir do cookie."""
    user = None
    user_id = None
    role = None
    table = None

    if request.cookies.get("cliente_id"):
        user_id = request.cookies.get("cliente_id")
        table = "clientes"
        role = "cliente"
    elif request.cookies.get("admin_id"):
        user_id = request.cookies.get("admin_id")
        table = "admin"
        role = "admin"

    if user_id and table:
        with db.cursor(dictionary=True) as cursor:
            cursor.execute(f"SELECT * FROM {table} WHERE id=%s", (user_id,))
            user = cursor.fetchone()
            if user:
                user['role'] = role
    return user

# ROTA PRINCIPAL (Página Inicial)
@app.get("/", response_class=HTMLResponse)
def read_home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html")

# LOGIN
@app.post("/login")
def login(request: Request, email: str = Form(...), senha: str = Form(...), db=Depends(get_db)):
    senha_hasheada = hash_senha(senha)
    with db.cursor(dictionary=True, buffered=True) as cursor:
        cursor.execute(
            "SELECT * FROM clientes WHERE email=%s AND senha=%s",
            (email, senha_hasheada)
        )
        user = cursor.fetchone()

    if user:
        # Criamos o redirecionamento e salvamos quem logou em um "cookie" (sessão simples)
        response = RedirectResponse(url="/pets", status_code=303)
        response.set_cookie(key="cliente_id", value=str(user["id"]), httponly=True)
        return response
    
    return templates.TemplateResponse(request=request, name="home.html", context={"msg_login": "E-mail ou senha incorretos."})

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("cliente_id")
    response.delete_cookie("admin_id")
    return response

# CADASTRO
@app.post("/cadastro")
def cadastro(
    request: Request,
    fullName: str = Form(...),
    email: str = Form(...),
    cpf: str = Form(...),
    birth: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db)
):
    with db.cursor(dictionary=True, buffered=True) as cursor:
        cursor.execute("SELECT * FROM clientes WHERE email=%s OR cpf=%s OR telefone=%s", (email, cpf, phone))
        cliente_existente = cursor.fetchone()
        if cliente_existente:
            if cliente_existente['email'] == email:
                error_field = "email"
                error_msg = "E-mail já está cadastrado."
            elif cliente_existente['cpf'] == cpf:
                error_field = "cpf"
                error_msg = "CPF já está cadastrado."
            else:
                error_field = "phone"
                error_msg = "Telefone já está cadastrado."
            
            return templates.TemplateResponse(request=request, name="home.html", context={
                "open_cadastro": True,
                "error_field": error_field,
                "error_msg": error_msg,
                "form_data": {"fullName": fullName, "email": email, "cpf": cpf, "birth": birth, "phone": phone}
            })
        
        senha_hasheada = hash_senha(password)
        cursor.execute(
            "INSERT INTO clientes (nome, email, cpf, nascimento, telefone, senha) VALUES (%s, %s, %s, %s, %s, %s)", 
            (fullName, email, cpf, birth, phone, senha_hasheada)
        )
        db.commit()

    return templates.TemplateResponse(request=request, name="home.html", context={"msg_login": "Conta criada com sucesso! Faça login.", "saved_email": email})

# ROTA PLANOS
@app.get("/planos", response_class=HTMLResponse)
def read_planos(request: Request):
    return templates.TemplateResponse(request=request, name="planos.html")

#PETS 
@app.get("/pets", response_class=HTMLResponse)
def listar_pets(request: Request, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)

    cliente_id = user['id']
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM pets WHERE cliente_id=%s", (cliente_id,))
        pets = cursor.fetchall()
        for pet in pets:
            pet['idade'] = calcular_idade(pet['nascimento'])
    return templates.TemplateResponse(request=request, name="pets.html", context={"pets": pets, "user": user})

@app.post("/pets")
def add_pet(request: Request, nome: str = Form(...), nascimento: str = Form(...),
            especie: str = Form(...), raca: str = Form(...),
            peso: float = Form(...), altura: float = Form(...),
            comprimento: float = Form(...), largura: float = Form(...),
            db=Depends(get_db), user: dict = Depends(get_current_user)):
    cliente_id = request.cookies.get("cliente_id")
    if not cliente_id:
        return RedirectResponse(url="/", status_code=303)

    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO pets (cliente_id, nome, nascimento, especie, raca, peso, altura, comprimento, largura) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (cliente_id, nome, nascimento, especie, raca, peso, altura, comprimento, largura)
        )
        db.commit()
    return RedirectResponse(url="/pets", status_code=303)

# AGENDA (Substitui o antigo /eventos GET)
@app.get("/agenda", response_class=HTMLResponse)
def listar_eventos(request: Request, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)

    with db.cursor(dictionary=True) as cursor:
        cliente_id = user['id']
        cursor.execute("""
            SELECT e.*, p.nome as pet_nome 
            FROM eventos e
            LEFT JOIN pets p ON e.pet_id = p.id
            WHERE p.cliente_id = %s
        """, (cliente_id,))
        eventos = cursor.fetchall()
        
        cursor.execute("SELECT * FROM pets WHERE cliente_id=%s", (cliente_id,))
        pets = cursor.fetchall()
        
    return templates.TemplateResponse(request=request, name="agenda.html", context={"eventos": eventos, "pets": pets, "user": user})

@app.post("/eventos")
def add_evento(pet_id: int = Form(...), data: str = Form(...),
               hora: str = Form(...), tipo: str = Form(...),
               descricao: str = Form(...), local: str = Form(""),
               observacoes: str = Form(""), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO eventos 
            (pet_id,data,hora,tipo,descricao,local,observacoes)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (pet_id, data, hora, tipo, descricao, local, observacoes))
        db.commit()
    return RedirectResponse(url="/agenda", status_code=303)

# DEMAIS PÁGINAS DA ÁREA DO CLIENTE
@app.get("/meu-plano", response_class=HTMLResponse)
def read_meu_plano(request: Request, user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="Meu_plano.html", context={"user": user})

@app.get("/calendario", response_class=HTMLResponse)
def read_calendario(request: Request, user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="calendario.html", context={"user": user})

# ==========================================
# ROTA DE PERFIL
# ==========================================
@app.get("/perfil", response_class=HTMLResponse)
def read_profile(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/", status_code=303)
    
    success_msg = request.query_params.get('success_msg')
    
    return templates.TemplateResponse(
        request=request, 
        name="perfil.html", 
        context={"user": user, "success_msg": success_msg}
    )

@app.post("/perfil")
async def update_profile(
    request: Request,
    db: mysql.connector.connection.MySQLConnection = Depends(get_db),
    user: dict = Depends(get_current_user),
    nome: str = Form(...),
    email: str = Form(...),
    telefone: str = Form(None),
    profile_pic: UploadFile = File(None)
):
    if not user:
        return RedirectResponse(url="/", status_code=303)

    user_id = user['id']
    profile_pic_url = user['profile_pic_url']

    if profile_pic and profile_pic.filename:
        Path("assets/img/profiles").mkdir(parents=True, exist_ok=True)
        timestamp = int(datetime.now().timestamp())
        file_extension = Path(profile_pic.filename).suffix
        file_path = f"assets/img/profiles/user_{user['role']}_{user_id}_{timestamp}{file_extension}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(profile_pic.file, buffer)
        profile_pic_url = "/" + file_path

    with db.cursor() as cursor:
        if user['role'] == 'cliente':
            cursor.execute("UPDATE clientes SET nome=%s, email=%s, telefone=%s, profile_pic_url=%s WHERE id=%s", (nome, email, telefone, profile_pic_url, user_id))
        elif user['role'] == 'admin':
            cursor.execute("UPDATE admin SET nome=%s, email=%s, profile_pic_url=%s WHERE id=%s", (nome, email, profile_pic_url, user_id))
        db.commit()

    return RedirectResponse(url="/perfil?success_msg=Perfil atualizado com sucesso!", status_code=303)

#FUNCIONARIOS
@app.get("/funcionarios")
def listar_funcionarios(db=Depends(get_db)):
    with db.cursor(dictionary=True) as cursor:
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

# ==========================================
# ROTAS ADMINISTRATIVAS
# ==========================================

@app.get("/login-admin", response_class=HTMLResponse)
def read_login_admin(request: Request):
    return templates.TemplateResponse(request=request, name="loginAdm.html")

@app.post("/login-admin")
def process_login_admin(request: Request, email: str = Form(...), senha: str = Form(...), db=Depends(get_db)):
    senha_hasheada = hash_senha(senha)
    with db.cursor(dictionary=True, buffered=True) as cursor:
        cursor.execute("SELECT * FROM admin WHERE email=%s AND senha=%s", (email, senha_hasheada))
        admin = cursor.fetchone()
    
    if admin:
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="admin_id", value=str(admin["id"]), httponly=True)
        return response
    
    return templates.TemplateResponse(request=request, name="loginAdm.html", context={"msg_login": "Credenciais inválidas."})

@app.get("/admin", response_class=HTMLResponse)
def painel_admin(request: Request, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'admin':
        return RedirectResponse(url="/login-admin", status_code=303)
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM cargos")
        cargos = cursor.fetchall()
        cursor.execute("SELECT * FROM funcionarios")
        funcionarios = cursor.fetchall()
        cursor.execute("SELECT id, nome, email, cpf, telefone FROM clientes")
        clientes = cursor.fetchall()
    return templates.TemplateResponse(request=request, name="admin.html", context={"cargos": cargos, "funcionarios": funcionarios, "clientes": clientes, "user": user})

@app.post("/admin/cargos")
def add_cargo_admin(nome: str = Form(...), db=Depends(get_db)):
    with db.cursor() as cursor:
        try:
            cursor.execute("INSERT INTO cargos (nome) VALUES (%s)", (nome,))
            db.commit()
        except:
            pass # Ignora se o cargo já existir
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/funcionarios")
def add_funcionario_admin(nome: str = Form(...), cargo: str = Form(...), salario: float = Form(...), telefone: str = Form(...), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("INSERT INTO funcionarios (nome, cargo, salario, telefone) VALUES (%s,%s,%s,%s)", (nome, cargo, salario, telefone))
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/funcionarios/{id}/deletar")
def deletar_funcionario_admin(id: int, db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM funcionarios WHERE id=%s", (id,))
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)