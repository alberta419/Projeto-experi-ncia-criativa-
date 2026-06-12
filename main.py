from urllib import request

from fastapi import FastAPI, Form, Depends, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mysql.connector
import os
from dotenv import load_dotenv
import hashlib
from datetime import date, datetime, timedelta
import logging
import mysql.connector.errors

app = FastAPI(debug=True)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# Logger básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_senha(senha: str) -> str:
    """Transforma a senha em um código SHA-256 irreversível"""
    return hashlib.sha256(senha.encode()).hexdigest()

def calcular_idade(ano_nascimento):
    """Calcula a idade aproximada com base no ano de nascimento."""
    if not ano_nascimento or not isinstance(ano_nascimento, int) or ano_nascimento <= 0:
        return "N/A"
    
    ano_atual = date.today().year
    idade = ano_atual - ano_nascimento
    
    if idade < 0:
        return "Idade inválida"
    if idade == 0:
        return "Menos de 1 ano"
    if idade == 1:
        return "1 ano"
    return f"{idade} anos"

def validar_cpf(cpf: str) -> bool:
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    digito1 = (soma * 10 % 11) % 10
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    digito2 = (soma * 10 % 11) % 10
    return cpf[-2:] == f"{digito1}{digito2}"

def get_db():
    """Cria uma conexão MySQL usando variáveis de ambiente.

    Variáveis suportadas: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT
    Valores padrão: localhost, root, root, petzen, 3306
    """
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "root")
    database = os.getenv("DB_NAME", "petzen")
    port = int(os.getenv("DB_PORT", "3306"))

    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        # Garante que a conexão seja fechada após o uso
        # Isso é importante para evitar que o pool de conexões se esgote
        # e para liberar recursos do banco de dados.
        # O FastAPI lida com o fechamento de dependências, mas um 'finally'
        # explícito aqui pode ser útil para depuração ou cenários específicos.
        conn.autocommit = True # Adicionado para garantir que as operações sejam commitadas imediatamente
        return conn
    except mysql.connector.Error as e:
        # Log detalhado para diagnóstico sem expor senha
        logger.exception("Falha ao conectar ao MySQL (%s:%s/%s): %s", host, port, database, e)
        # Levanta uma exceção clara para o FastAPI retornar 500
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados. Verifique as configurações e se o MySQL está rodando.")


@app.on_event('startup')
def check_db_on_startup():
    """Verifica a conexão com o banco ao iniciar a aplicação e loga o resultado."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor(buffered=True) as cursor:
            cursor.execute('SELECT 1')
            # Consumir o resultado evita erro 'Unread result found' ao fechar o cursor
            _ = cursor.fetchone()
        logger.info('Conexão com o banco de dados verificada com sucesso.')
    except HTTPException as he:
        logger.error('Startup: conexão com DB falhou: %s', he.detail)
    except Exception as e:
        logger.exception('Startup: erro inesperado ao verificar DB: %s', e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

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
def read_home(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="home.html", context={"user": user})

# LOGIN
# 1. ROTA QUE PROCESSA O ENVIO DO FORMULÁRIO (POST)
# LOGIN
# 1. ROTA QUE PROCESSA O ENVIO DO FORMULÁRIO (POST)
@app.post("/login")
def login(request: Request, email: str = Form(...), senha: str = Form(...), db=Depends(get_db)):
    senha_hasheada = hash_senha(senha)
    
    with db.cursor(dictionary=True, buffered=True) as cursor:
        cursor.execute(
            "SELECT * FROM clientes WHERE email=%s AND senha=%s",
            (email, senha_hasheada)
        )
        user = cursor.fetchone()

    # Se o utilizador não existir ou a senha estiver errada
    if not user:
        # CORREÇÃO: Sintaxe nomeada para evitar o erro 500 no Python 3.14
        return templates.TemplateResponse(
            name="home.html",
            context={
                "request": request,
                "msg_login": "E-mail ou senha incorretos.",
                "saved_email": email
            },
            request=request
        )

    # Se o login for bem-sucedido:
    response = RedirectResponse(url="/pets", status_code=303)
    response.set_cookie(key="cliente_id", value=str(user["id"]), httponly=True)
    return response


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="home.html", 
        context={"open_login": True}
    )


# 3. ROTA QUE RENDERIZA A PÁGINA INTERNA DA ÁREA DO CLIENTE
@app.get("/area_cliente", response_class=HTMLResponse)
def area_cliente(request: Request, user: dict = Depends(get_current_user)):
    # Garante que apenas clientes logados entram
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/login", status_code=303)
        
    return templates.TemplateResponse(request=request, name="area_cliente.html", context={"user": user})

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
    confirmPassword: str = Form(...),   # ← adicione este campo
    db=Depends(get_db)
):
    # Validar CPF
    if not validar_cpf(cpf):
        return templates.TemplateResponse(request=request, name="home.html", context={
            "open_cadastro": True,
            "error_field": "cpf",
            "error_msg": "CPF inválido.",
            "form_data": {"fullName": fullName, "email": email, "cpf": cpf, "birth": birth, "phone": phone}
        })

    # Validar confirmação de senha (segurança extra no backend)
    if password != confirmPassword:
        return templates.TemplateResponse(request=request, name="home.html", context={
            "open_cadastro": True,
            "error_field": "password",
            "error_msg": "As senhas não coincidem.",
            "form_data": {"fullName": fullName, "email": email, "cpf": cpf, "birth": birth, "phone": phone}
        })

    # Converter data
    try:
        birth_formatted = datetime.strptime(birth, '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        return templates.TemplateResponse(request=request, name="home.html", context={
            "open_cadastro": True,
            "error_field": "birth",
            "error_msg": "Formato de data inválido. Use DD/MM/AAAA.",
            "form_data": {"fullName": fullName, "email": email, "cpf": cpf, "birth": birth, "phone": phone}
        })

    try:
        with db.cursor(dictionary=True, buffered=True) as cursor:
            # Verificar duplicatas
            cursor.execute(
                "SELECT email, cpf, telefone FROM clientes WHERE email=%s OR cpf=%s OR telefone=%s",
                (email, cpf, phone)
            )
            cliente_existente = cursor.fetchone()
            if cliente_existente:
                if cliente_existente['email'] == email:
                    error_field, error_msg = "email", "E-mail já está cadastrado."
                elif cliente_existente['cpf'] == cpf:
                    error_field, error_msg = "cpf", "CPF já está cadastrado."
                else:
                    error_field, error_msg = "phone", "Telefone já está cadastrado."

                return templates.TemplateResponse(request=request, name="home.html", context={
                    "open_cadastro": True,
                    "error_field": error_field,
                    "error_msg": error_msg,
                    "form_data": {"fullName": fullName, "email": email, "cpf": cpf, "birth": birth, "phone": phone}
                })

            senha_hasheada = hash_senha(password)
            cursor.execute(
                "INSERT INTO clientes (nome, email, cpf, nascimento, telefone, senha) VALUES (%s, %s, %s, %s, %s, %s)",
                (fullName, email, cpf, birth_formatted, phone, senha_hasheada)
            )
        db.commit()   # ← commit FORA do with, mas antes de fechar

    except mysql.connector.errors.IntegrityError as e:
        logger.error("Erro de integridade ao cadastrar cliente: %s", e)
        return templates.TemplateResponse(request=request, name="home.html", context={
            "open_cadastro": True,
            "error_msg": "Erro ao salvar cadastro. Tente novamente.",
        })
    finally:
        db.close()   # ← SEMPRE fecha a conexão

    return templates.TemplateResponse(request=request, name="home.html", context={
        "msg_login": "Conta criada com sucesso! Faça login.",
        "saved_email": email
    })

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
            # A chave aqui deve ser a mesma do seu banco de dados ('ano_nascimento')
            pet['idade'] = calcular_idade(pet.get('ano_nascimento'))
    return templates.TemplateResponse(request=request, name="pets.html", context={"pets": pets, "user": user})

@app.post("/pets")
def add_pet(request: Request, nome: str = Form(...), ano_nascimento: int = Form(...),
            especie: str = Form(...), raca: str = Form(...),
            peso: float = Form(...), db=Depends(get_db), 
            user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)

    # Lembre-se de ter executado o comando SQL para alterar a coluna no banco de dados
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO pets (cliente_id, nome, ano_nascimento, especie, raca, peso) VALUES (%s, %s, %s, %s, %s, %s)",
            (user['id'], nome, ano_nascimento, especie, raca, peso)
        )
        db.commit()
    return RedirectResponse(url="/pets", status_code=303)

#EDITAR E DELETAR PETS
@app.post("/pets/{pet_id}/editar")
def editar_pet(
    pet_id: int,
    request: Request,
    nome: str = Form(...),
    ano_nascimento: int = Form(...),
    especie: str = Form(...),
    raca: str = Form(...),
    peso: float = Form(...),
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)
    
    with db.cursor() as cursor:
        cursor.execute(
            "UPDATE pets SET nome=%s, ano_nascimento=%s, especie=%s, raca=%s, peso=%s WHERE id=%s AND cliente_id=%s",
            (nome, ano_nascimento, especie, raca, peso, pet_id, user['id'])
        )
        db.commit()
    return RedirectResponse(url="/pets", status_code=303)


@app.post("/pets/{pet_id}/deletar")
def deletar_pet(
    pet_id: int,
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)
    
    with db.cursor() as cursor:
        # Remove os eventos do pet antes de deletar
        cursor.execute("DELETE FROM eventos WHERE pet_id=%s", (pet_id,))
        cursor.execute("DELETE FROM pets WHERE id=%s AND cliente_id=%s", (pet_id, user['id']))
        db.commit()
    return RedirectResponse(url="/pets", status_code=303)


# ==========================================
# ROTAS DE PLANOS POR PET
# ==========================================
@app.get("/pets/{pet_id}/plano", response_class=HTMLResponse)
def get_pet_plano(pet_id: int, request: Request, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)
    
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM pets WHERE id=%s AND cliente_id=%s", (pet_id, user['id']))
        pet = cursor.fetchone()
    
    if not pet:
        return RedirectResponse(url="/pets", status_code=404)
        
    return templates.TemplateResponse(request=request, name="planos_pet.html", context={"pet": pet, "user": user})

@app.post("/pets/{pet_id}/plano")
def update_pet_plano(pet_id: int, plano: str = Form(...), db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)

    with db.cursor() as cursor:
        cursor.execute("UPDATE pets SET plano=%s WHERE id=%s AND cliente_id=%s", (plano, pet_id, user['id']))
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
            SELECT e.*, p.nome as pet_nome, f.nome as funcionario_nome
            FROM eventos e LEFT JOIN pets p ON e.pet_id = p.id
            LEFT JOIN funcionarios f ON e.funcionario_id = f.id
            WHERE p.cliente_id = %s ORDER BY e.data ASC, e.hora ASC
        """, (cliente_id,))
        eventos = cursor.fetchall()

        # Formata a hora de cada evento para uma exibição mais limpa (HH:MM)
        for evento in eventos:
            if isinstance(evento.get('hora'), timedelta):
                total_seconds = int(evento['hora'].total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                evento['hora'] = f"{hours:02d}:{minutes:02d}"
        
        cursor.execute("SELECT * FROM pets WHERE cliente_id=%s", (cliente_id,))
        pets = cursor.fetchall()

        # Busca os funcionários que podem ser selecionados para agendamentos
        cursor.execute("SELECT id, nome, cargo FROM funcionarios WHERE cargo IN ('Veterinário', 'Banhista')")
        funcionarios = cursor.fetchall()

    context = {
        "request": request,
        "eventos": eventos, 
        "pets": pets, 
        "funcionarios": funcionarios,
        "user": user,
        "success_msg": request.query_params.get('success_msg'),
        "error_msg": request.query_params.get('error_msg')
    }
    return templates.TemplateResponse(request=request, name="agenda.html", context=context)

@app.get("/api/horarios-disponiveis")
def get_horarios_disponiveis(data: str, tipo: str, funcionario_id: int, db=Depends(get_db)):
    """
    API para retornar uma lista de horários disponíveis para um funcionário,
    baseado no tipo de serviço e nos agendamentos já existentes.
    """
    try:
        data_selecionada = datetime.strptime(data, '%Y-%m-%d').date()
        # Impede agendamentos em datas passadas
        if data_selecionada < date.today():
            return []
    except ValueError:
        return {"error": "Formato de data inválido"}

    duracoes = {"Banho e Tosa": 90, "Consulta": 30, "Vacina": 30, "Exame": 60}
    duracao_servico_req = timedelta(minutes=duracoes.get(tipo, 60))

    # Buscar agendamentos existentes para o funcionário no dia
    agendamentos_ocupados = []
    with db.cursor(dictionary=True) as cursor:
        cursor.execute(
            "SELECT hora, tipo FROM eventos WHERE funcionario_id = %s AND data = %s",
            (funcionario_id, data_selecionada)
        )
        for evento in cursor.fetchall():
            # A hora vem do banco como timedelta, precisamos converter para time
            if isinstance(evento['hora'], timedelta):
                total_seconds = int(evento['hora'].total_seconds())
                hora_inicio = (datetime.min + timedelta(seconds=total_seconds)).time()
            else: # Se vier como string ou time, o parsing manual é mais seguro
                # O formato de str(timedelta) é 'H:MM:SS', que pode falhar no strptime com horas de um dígito.
                # O formato de str(time) é 'HH:MM:SS'. O split() lida com ambos os casos.
                h, m, s = map(int, str(evento['hora']).split(':'))
                hora_inicio = datetime.time(h, m, s)

            duracao_evento = timedelta(minutes=duracoes.get(evento['tipo'], 60))
            inicio_evento_dt = datetime.combine(data_selecionada, hora_inicio)
            fim_evento_dt = inicio_evento_dt + duracao_evento
            agendamentos_ocupados.append((inicio_evento_dt, fim_evento_dt))

    # Gerar todos os slots possíveis (a cada 30 min) e verificar disponibilidade
    horarios_disponiveis = []
    inicio_trabalho = datetime.combine(data_selecionada, datetime.strptime("08:00", "%H:%M").time())
    fim_trabalho = datetime.combine(data_selecionada, datetime.strptime("18:00", "%H:%M").time())
    slot_atual = inicio_trabalho

    while slot_atual < fim_trabalho:
        fim_slot_proposto = slot_atual + duracao_servico_req
        if fim_slot_proposto > fim_trabalho:
            break # O serviço terminaria após o expediente

        # Verificar se o slot proposto se sobrepõe a algum agendamento existente
        slot_livre = True
        for inicio_ocupado, fim_ocupado in agendamentos_ocupados:
            if max(slot_atual, inicio_ocupado) < min(fim_slot_proposto, fim_ocupado):
                slot_livre = False
                break
        
        if slot_livre:
            horarios_disponiveis.append(slot_atual.strftime("%H:%M"))
        
        slot_atual += timedelta(minutes=30) # Próximo slot possível

    return horarios_disponiveis

@app.post("/eventos")
def add_evento(request: Request, pet_id: int = Form(...), funcionario_id: int = Form(...), data: str = Form(...),
            hora: str = Form(...), tipo: str = Form(...),
            descricao: str = Form(...), db=Depends(get_db),
            user: dict = Depends(get_current_user)):

    if not user or user.get('role') != 'cliente':
        return RedirectResponse(url="/", status_code=303)

    with db.cursor(dictionary=True, buffered=True) as cursor:
        # 1. Busca o plano do pet e verifica se o pet pertence ao usuário logado
        cursor.execute("SELECT plano FROM pets WHERE id=%s AND cliente_id=%s", (pet_id, user['id']))
        pet = cursor.fetchone()

        if not pet:
            return RedirectResponse(url="/agenda?error_msg=Pet não encontrado.", status_code=303)

        # 2. VALIDAÇÃO DE HORÁRIO (Anti-Race Condition)
        # Verifica se o horário exato não foi agendado por outra pessoa enquanto o cliente preenchia o formulário
        hora_formatada = f"{hora}:00"
        cursor.execute(
            "SELECT id FROM eventos WHERE funcionario_id = %s AND data = %s AND hora = %s",
            (funcionario_id, data, hora_formatada)
        )
        if cursor.fetchone():
            error_msg = "Oops! Este horário foi agendado por outra pessoa. Por favor, escolha outro."
            return RedirectResponse(url=f"/agenda?error_msg={error_msg}", status_code=303)

        # 3. Aplica a regra para o Plano Básico
        if pet.get('plano') == 'Básico' and tipo == 'Banho e Tosa':
            try:
                event_date = datetime.strptime(data, '%Y-%m-%d')
                # Conta quantos banhos e tosas o pet já tem no mês do agendamento
                cursor.execute("""
                    SELECT COUNT(*) as count FROM eventos 
                    WHERE pet_id = %s AND tipo = 'Banho e Tosa' 
                    AND MONTH(data) = %s AND YEAR(data) = %s
                """, (pet_id, event_date.month, event_date.year))
                
                if cursor.fetchone()['count'] >= 1:
                    error_msg = "Limite de 1 Banho e Tosa por mês para o Plano Básico foi atingido."
                    return RedirectResponse(url=f"/agenda?error_msg={error_msg}", status_code=303)
            except (ValueError, KeyError):
                return RedirectResponse(url="/agenda?error_msg=Data inválida.", status_code=303)

    # 4. Se todas as regras passarem, insere o evento no banco
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO eventos 
            (pet_id, funcionario_id, data, hora, tipo, descricao)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (pet_id, funcionario_id, data, hora, tipo, descricao))
        db.commit()
    return RedirectResponse(url="/agenda?success_msg=Agendamento realizado com sucesso!", status_code=303)

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

    pic_data = None
    if profile_pic and profile_pic.filename:
        # Lê o conteúdo do arquivo enviado como bytes
        pic_data = await profile_pic.read()

    with db.cursor() as cursor:
        if user['role'] == 'cliente':
            if pic_data:
                # Se uma nova foto foi enviada, atualiza a coluna profile_pic
                cursor.execute("UPDATE clientes SET nome=%s, email=%s, telefone=%s, profile_pic=%s WHERE id=%s", (nome, email, telefone, pic_data, user['id']))
            else:
                # Caso contrário, atualiza apenas os outros dados
                cursor.execute("UPDATE clientes SET nome=%s, email=%s, telefone=%s WHERE id=%s", (nome, email, telefone, user['id']))
        elif user['role'] == 'admin':
            if pic_data:
                cursor.execute("UPDATE admin SET nome=%s, email=%s, profile_pic=%s WHERE id=%s", (nome, email, pic_data, user['id']))
            else:
                cursor.execute("UPDATE admin SET nome=%s, email=%s WHERE id=%s", (nome, email, user['id']))
        db.commit()

    return RedirectResponse(url="/perfil?success_msg=Perfil atualizado com sucesso!", status_code=303)

@app.get("/profile-pic/{role}/{user_id}")
async def get_user_profile_pic(role: str, user_id: int, db: mysql.connector.connection.MySQLConnection = Depends(get_db)):
    """Endpoint para servir a imagem de perfil a partir do BLOB no banco de dados."""
    if role not in ['cliente', 'admin']:
        return Response(status_code=404)
    
    table = "clientes" if role == 'cliente' else 'admin'
    
    with db.cursor(dictionary=True) as cursor:
        cursor.execute(f"SELECT profile_pic FROM {table} WHERE id=%s", (user_id,))
        result = cursor.fetchone()
    
    pic_data = result.get('profile_pic') if result else None

    if not pic_data:
        # SOLUÇÃO: Em vez de depender de um arquivo, geramos um SVG padrão.
        # Isso evita erros caso o 'default-profile.png' não exista e simplifica o projeto.
        svg_content = """
        <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="100" fill="#e0e0e0"/>
            <path d="M50 45C41.7157 45 35 38.2843 35 30C35 21.7157 41.7157 15 50 15C58.2843 15 65 21.7157 65 30C65 38.2843 58.2843 45 50 45ZM20 85V75C20 66.1634 26.7157 55 40 55H60C73.2843 55 80 66.1634 80 75V85H20Z" fill="#a0a0a0"/>
        </svg>
        """
        return Response(content=svg_content, media_type="image/svg+xml")

    return Response(content=pic_data, media_type="image/jpeg")

# ==========================================
# ROTAS ADMINISTRATIVAS
# ==========================================

@app.get("/login-admin", response_class=HTMLResponse)
def read_login_admin(request: Request):
    # Solução definitiva: Nomeando os 3 parâmetros fundamentais de forma explícita
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
    
    # Solução definitiva: Nomeando aqui também para evitar o erro de POST
    return templates.TemplateResponse(
    request=request,
    name="loginAdm.html",
    context={"msg_login": "Credenciais inválidas."}
)
    
@app.get("/admin", response_class=HTMLResponse)
def painel_admin(request: Request, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'admin':
        return RedirectResponse(url="/login-admin", status_code=303)
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM cargos")
        cargos = cursor.fetchall()
        cursor.execute("SELECT * FROM funcionarios")
        funcionarios = cursor.fetchall()

        # Pega todos os clientes, ordenados por nome
        cursor.execute("SELECT id, nome, email, cpf, telefone FROM clientes ORDER BY nome")
        clientes = cursor.fetchall()

        # Pega todos os pets para associar com seus donos
        cursor.execute("SELECT id, nome, especie, cliente_id FROM pets")
        all_pets = cursor.fetchall()

        # Cria um dicionário para mapear os pets a cada ID de cliente
        pets_by_client = {}
        for pet in all_pets:
            client_id = pet['cliente_id']
            if client_id not in pets_by_client:
                pets_by_client[client_id] = []
            pets_by_client[client_id].append(pet)

        # Anexa a lista de pets a cada dicionário de cliente
        for cliente in clientes:
            cliente['pets'] = pets_by_client.get(cliente['id'], [])

        # Mantém a query original de pets para a lista geral de pets no painel
        cursor.execute("""
            SELECT p.*, c.nome as cliente_nome
            FROM pets p
            JOIN clientes c ON p.cliente_id = c.id
            ORDER BY c.nome
        """)
        pets = cursor.fetchall()
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "cargos": cargos,
        "funcionarios": funcionarios,
        "clientes": clientes, # A lista de clientes agora contém os pets de cada um
        "pets": pets,
        "user": user
    })
    
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

@app.post("/admin/funcionarios/{id}/editar")
def editar_funcionario_admin(
    id: int,
    nome: str = Form(...),
    cargo: str = Form(...),
    salario: float = Form(...),
    telefone: str = Form(...),
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if not user or user.get('role') != 'admin':
        return RedirectResponse(url="/login-admin", status_code=303)
    with db.cursor() as cursor:
        cursor.execute(
            "UPDATE funcionarios SET nome=%s, cargo=%s, salario=%s, telefone=%s WHERE id=%s",
            (nome, cargo, salario, telefone, id)
        )
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/pets/{id}/deletar")
def deletar_pet_admin(id: int, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not user or user.get('role') != 'admin':
        return RedirectResponse(url="/login-admin", status_code=303)
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM eventos WHERE pet_id=%s", (id,))
        cursor.execute("DELETE FROM pets WHERE id=%s", (id,))
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/clientes/{id}/deletar")
def deletar_cliente_admin(id: int, db=Depends(get_db), user: dict = Depends(get_current_user)):
    """Rota para o admin deletar um cliente e todos os seus dados associados."""
    if not user or user.get('role') != 'admin':
        return RedirectResponse(url="/login-admin", status_code=303)
    
    with db.cursor() as cursor:
        # Para manter a integridade, deletamos os registros que dependem do cliente
        # 1. Deleta os eventos dos pets do cliente
        cursor.execute("DELETE FROM eventos WHERE pet_id IN (SELECT id FROM pets WHERE cliente_id = %s)", (id,))
        # 2. Deleta os pets do cliente
        cursor.execute("DELETE FROM pets WHERE cliente_id = %s", (id,))
        # 3. Deleta o cliente
        cursor.execute("DELETE FROM clientes WHERE id = %s", (id,))
        db.commit()
    return RedirectResponse(url="/admin?success_msg=Cliente deletado com sucesso!", status_code=303)

# Teste de conexão usando a mesma lógica da aplicação
try:
    conn = get_db()
    if conn.is_connected():
        db_info = conn.get_server_info()
        print(f"\n🚀 SUCESSO: Conectado ao banco '{conn.database}' (Versão {db_info})\n")
        conn.close()
except Exception as e:
    print(f"\n❌ ERRO DE CONEXÃO: Verifique se o banco '{os.getenv('DB_NAME', 'petzen')}' existe no MySQL. Erro: {e}\n")
    
@app.post("/admin/clientes/{id}/editar")
def editar_cliente_admin(
    id: int,
    nome: str = Form(...),
    email: str = Form(...),
    cpf: str = Form(...),
    telefone: str = Form(...),
    db=Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if not user or user.get('role') != 'admin':
        return RedirectResponse(url="/login-admin", status_code=303)
    
    with db.cursor() as cursor:
        cursor.execute(
            "UPDATE clientes SET nome=%s, email=%s, cpf=%s, telefone=%s WHERE id=%s",
            (nome, email, cpf, telefone, id)
        )
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)