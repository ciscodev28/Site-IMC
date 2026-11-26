
import os
import json
import tempfile
import uuid
import math

from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from dotenv import load_dotenv


# ============================================================
# CONFIGURACAO
# ============================================================

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("Configure uma SECRET_KEY forte no arquivo .env")


ARQUIVO_BANCO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "database.json"
)

FOTO_PADRAO = "static/images/default-avatar.png"

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads"
)

EXTENSOES_PERMITIDAS = (
    "jpg",
    "jpeg",
    "png",
    "webp"
)

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def salvar_foto_perfil(arquivo):

    if not arquivo or not arquivo.filename:
        return None

    nome_original = secure_filename(arquivo.filename)

    if "." not in nome_original:
        raise ValueError("Arquivo de imagem inválido.")

    extensao = nome_original.rsplit(".", 1)[1].lower()

    if extensao not in EXTENSOES_PERMITIDAS:
        raise ValueError("Formato de imagem não permitido.")

    nome_arquivo = f"{uuid.uuid4().hex}.{extensao}"

    caminho = os.path.join(
        UPLOAD_FOLDER,
        nome_arquivo
    )

    arquivo.save(caminho)

    return f"static/uploads/{nome_arquivo}"


# ============================================================
# PERSISTENCIA DE DADOS
# ============================================================

def inicializar_banco():
    """Cria a pasta e o JSON caso ainda nao existam."""
    os.makedirs(os.path.dirname(ARQUIVO_BANCO), exist_ok=True)

    if not os.path.exists(ARQUIVO_BANCO):
        with open(ARQUIVO_BANCO, "w", encoding="utf-8") as arquivo:
            json.dump([], arquivo, ensure_ascii=False, indent=4)


def carregar_usuarios():
    """Carrega os registros e aplica valores padrao a campos novos."""
    inicializar_banco()

    try:
        with open(ARQUIVO_BANCO, "r", encoding="utf-8") as arquivo:
            usuarios = json.load(arquivo)

    except json.JSONDecodeError as erro:
        raise RuntimeError(
            "O arquivo data/database.json contem JSON invalido. "
            "Corrija o arquivo antes de continuar."
        ) from erro

    if not isinstance(usuarios, list):
        raise RuntimeError(
            "O database.json deve conter uma lista de usuarios."
        )

    alterado = False

    for usuario in usuarios:

        if "excluido" not in usuario:
            usuario["excluido"] = False
            alterado = True

        if "funcao" not in usuario:
            usuario["funcao"] = "comum"
            alterado = True

        if "foto_perfil" not in usuario:
            usuario["foto_perfil"] = FOTO_PADRAO
            alterado = True

    if alterado:
        salvar_usuarios(usuarios)

    return usuarios


def salvar_usuarios(usuarios):
    """Salva o JSON de forma segura, evitando arquivo parcialmente gravado."""
    inicializar_banco()

    pasta = os.path.dirname(ARQUIVO_BANCO)
    caminho_temporario = None

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=pasta,
            delete=False
        ) as arquivo:

            json.dump(
                usuarios,
                arquivo,
                ensure_ascii=False,
                indent=4
            )

            caminho_temporario = arquivo.name

        os.replace(caminho_temporario, ARQUIVO_BANCO)

    finally:
        if caminho_temporario and os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)


inicializar_banco()


# ============================================================
# FUNCOES AUXILIARES DE USUARIOS
# ============================================================

def buscar_usuario_por_id(usuario_id):

    for usuario in carregar_usuarios():

        if usuario.get("id") == usuario_id:
            return usuario

    return None


def listar_usuarios():
    """Retorna todos os usuarios para o painel, sem hashes de senha."""

    campos_publicos = (
        "id", "nome", "email", "data_cadastro",
        "funcao", "excluido", "foto_perfil"
    )

    resultado = []

    for usuario in carregar_usuarios():

        resultado.append({
            campo: usuario.get(campo)
            for campo in campos_publicos
        })

    return resultado


def contar_administradores_ativos(usuarios=None):

    if usuarios is None:
        usuarios = carregar_usuarios()

    return sum(
        1 for usuario in usuarios
        if usuario.get("funcao") == "admin"
        and not usuario.get("excluido", False)
    )


def criar_usuario(nome, email, senha, funcao="comum", foto_perfil=None):
    """Cria usuario; a funcao e comum por padrao."""

    usuarios = carregar_usuarios()

    nome = (nome or "").strip()
    email = (email or "").strip().lower()
    senha = senha or ""

    if not nome or not email or not senha:
        raise ValueError("Nome, e-mail e senha sao obrigatorios.")

    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Informe um e-mail valido.")

    if len(senha) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")

    if any(
        usuario.get("email", "").strip().lower() == email
        for usuario in usuarios
    ):
        raise ValueError("Este e-mail ja esta cadastrado.")

    if funcao not in ("comum", "admin"):
        raise ValueError("Funcao de usuario invalida.")

    novo_id = max(
        (usuario.get("id", 0) for usuario in usuarios),
        default=0
    ) + 1

    novo_usuario = {
        "id": novo_id,
        "nome": nome,
        "email": email,
        "senha_hash": generate_password_hash(
            senha,
            method="pbkdf2:sha256"
        ),
        "foto_perfil": foto_perfil or FOTO_PADRAO,
        "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "funcao": funcao,
        "excluido": False
    }

    usuarios.append(novo_usuario)
    salvar_usuarios(usuarios)

    return novo_usuario


def editar_usuario(usuario_id, nome, email, senha=None, foto_perfil=None):
    """Atualiza nome, e-mail, senha e, opcionalmente, a foto."""

    usuarios = carregar_usuarios()

    nome = (nome or "").strip()
    email = (email or "").strip().lower()
    senha = senha or ""

    if not nome or not email:
        raise ValueError("Nome e e-mail sao obrigatorios.")

    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Informe um e-mail valido.")

    usuario_alvo = None

    for usuario in usuarios:

        if usuario.get("id") == usuario_id:
            usuario_alvo = usuario
            break

    if usuario_alvo is None or usuario_alvo.get("excluido", False):
        raise ValueError("Usuario nao encontrado ou desativado.")

    for usuario in usuarios:

        if (
            usuario.get("id") != usuario_id
            and usuario.get("email", "").strip().lower() == email
        ):
            raise ValueError("Este e-mail ja esta sendo utilizado.")

    usuario_alvo["nome"] = nome
    usuario_alvo["email"] = email

    if senha:

        if len(senha) < 8:
            raise ValueError(
                "A nova senha deve ter pelo menos 8 caracteres."
            )

        usuario_alvo["senha_hash"] = generate_password_hash(
            senha,
            method="pbkdf2:sha256"
        )

    if foto_perfil:
        usuario_alvo["foto_perfil"] = foto_perfil

    salvar_usuarios(usuarios)

    return True


def alterar_funcao_usuario(usuario_id, nova_funcao, administrador_atual_id):
    """Permite ao administrador alterar a funcao sem remover o ultimo admin."""

    if nova_funcao not in ("comum", "admin"):
        raise ValueError("Funcao invalida.")

    usuarios = carregar_usuarios()

    alvo = next(
        (u for u in usuarios if u.get("id") == usuario_id),
        None
    )

    if alvo is None or alvo.get("excluido", False):
        raise ValueError("Usuario nao encontrado ou desativado.")

    if (
        alvo.get("funcao") == "admin"
        and nova_funcao != "admin"
        and contar_administradores_ativos(usuarios) <= 1
    ):
        raise ValueError(
            "Nao e possivel remover o ultimo administrador."
        )

    alvo["funcao"] = nova_funcao
    salvar_usuarios(usuarios)

    if usuario_id == administrador_atual_id:
        session["funcao"] = nova_funcao

    return True


def excluir_usuario(usuario_id):
    """Exclusao logica: preserva o registro no database.json."""

    usuarios = carregar_usuarios()

    alvo = next(
        (u for u in usuarios if u.get("id") == usuario_id),
        None
    )

    if alvo is None or alvo.get("excluido", False):
        return False

    if (
        alvo.get("funcao") == "admin"
        and contar_administradores_ativos(usuarios) <= 1
    ):
        raise ValueError(
            "Nao e possivel excluir o ultimo administrador."
        )

    alvo["excluido"] = True
    salvar_usuarios(usuarios)

    return True


def reativar_usuario(usuario_id):

    usuarios = carregar_usuarios()

    alvo = next(
        (u for u in usuarios if u.get("id") == usuario_id),
        None
    )

    if alvo is None or not alvo.get("excluido", False):
        return False

    alvo["excluido"] = False
    salvar_usuarios(usuarios)

    return True


# ============================================================
# DECORADORES DE AUTENTICACAO E AUTORIZACAO
# ============================================================

def login_required(funcao):

    @wraps(funcao)
    def decorada(*args, **kwargs):

        user_id = session.get("user_id")

        if user_id is None:
            abort(401)

        usuario = buscar_usuario_por_id(user_id)

        if usuario is None or usuario.get("excluido", False):
            session.clear()
            abort(401)

        # Mantem os dados essenciais da sessao sincronizados com o JSON.
        session["email"] = usuario["email"]
        session["funcao"] = usuario["funcao"]

        return funcao(*args, **kwargs)

    return decorada


def admin_required(funcao):

    @wraps(funcao)
    def decorada(*args, **kwargs):

        user_id = session.get("user_id")

        if user_id is None:
            abort(401)

        usuario = buscar_usuario_por_id(user_id)

        if usuario is None or usuario.get("excluido", False):
            session.clear()
            abort(401)

        session["email"] = usuario["email"]
        session["funcao"] = usuario["funcao"]

        if session.get("funcao") != "admin":
            abort(403)

        return funcao(*args, **kwargs)

    return decorada


# ============================================================
# PAGINAS PUBLICAS
# ============================================================

@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/sobre")
def sobre():
    return render_template("about.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        nome = request.form.get("nome", "")
        email = request.form.get("email", "")
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        arquivo_foto = request.files.get("foto_perfil")

        if senha != confirmar_senha:

            return render_template(
                "register.html",
                mensagem_erro="As senhas não coincidem",
                nome=nome,
                email=email
            )

        # Cadastro publico nunca permite escolher funcao admin.
        try:

            foto = salvar_foto_perfil(arquivo_foto)

            criar_usuario(
                nome,
                email,
                senha,
                funcao="comum",
                foto_perfil=foto
            )

            flash(
                "Cadastro realizado com sucesso! Faca seu login.",
                "success"
            )

            return redirect(url_for("login"))

        except ValueError as erro:

            return render_template(
                "register.html",
                mensagem_erro=str(erro),
                nome=nome,
                email=email
            )

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        usuarios = carregar_usuarios()

        usuario = next(
            (
                u for u in usuarios
                if u.get("email", "").strip().lower() == email
            ),
            None
        )

        if (
            usuario is None
            or usuario.get("excluido", False)
            or not check_password_hash(usuario.get("senha_hash", ""), senha)
        ):

            return render_template(
                "login.html",
                mensagem_erro="E-mail ou senha incorretos.",
                email=email
            )

        session.clear()
        session["user_id"] = usuario["id"]
        session["email"] = usuario["email"]
        session["funcao"] = usuario["funcao"]

        flash("Login realizado com sucesso!", "success")

        return redirect(url_for("inicio"))

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    flash("Voce saiu da sua conta.", "success")

    return redirect(url_for("login"))


# ============================================================
# PERFIL E EDICAO DA PROPRIA CONTA
# ============================================================

@app.route("/profile")
@login_required
def perfil():

    usuario = buscar_usuario_por_id(session["user_id"])

    return render_template(
        "profile.html",
        nome=usuario["nome"],
        email=usuario["email"],
        funcao=usuario["funcao"],
        foto_perfil=usuario.get("foto_perfil", FOTO_PADRAO),
        data_cadastro=usuario.get("data_cadastro"),
        dados_imc = usuario.get("dados_imc")
    )


@app.route("/editar-perfil", methods=["GET", "POST"])
@login_required
def editar_perfil():

    usuario_id = session["user_id"]
    usuario = buscar_usuario_por_id(usuario_id)

    if request.method == "POST":

        nome = request.form.get("nome", "")
        email = request.form.get("email", "")
        senha = request.form.get("senha", "")

        arquivo_foto = request.files.get("foto_perfil")

        try:

            foto = None

            if arquivo_foto and arquivo_foto.filename:
                foto = salvar_foto_perfil(arquivo_foto)

            editar_usuario(
                usuario_id,
                nome,
                email,
                senha,
                foto_perfil=foto
            )

            usuario_atualizado = buscar_usuario_por_id(usuario_id)
            session["email"] = usuario_atualizado["email"]

            flash("Perfil atualizado com sucesso!", "success")

            return redirect(url_for("perfil"))

        except ValueError as erro:

            usuario = buscar_usuario_por_id(usuario_id)

            return render_template(
                "edit-user.html",
                usuario=usuario,
                mensagem_erro=str(erro),
                admin_editando=False
            )

    return render_template(
        "edit-user.html",
        usuario=usuario,
        admin_editando=False
    )


@app.route("/excluir-conta", methods=["POST"])
@login_required
def excluir_propria_conta():

    usuario_id = session["user_id"]

    try:

        if excluir_usuario(usuario_id):

            session.clear()

            flash("Sua conta foi desativada.", "success")

            return redirect(url_for("inicio"))

        flash("Nao foi possivel desativar sua conta.", "error")

        return redirect(url_for("perfil"))

    except ValueError as erro:

        flash(str(erro), "error")

        return redirect(url_for("perfil"))


# ============================================================
# PAINEL E GERENCIAMENTO ADMINISTRATIVO
# ============================================================

@app.route("/admin/painel")
@admin_required
def painel_admin():

    usuarios = listar_usuarios()

    total = len(usuarios)
    ativos = sum(1 for u in usuarios if not u["excluido"])
    excluidos = total - ativos

    administradores = sum(
        1 for u in usuarios
        if u["funcao"] == "admin" and not u["excluido"]
    )

    estatisticas = {
        "total": total,
        "ativos": ativos,
        "excluidos": excluidos,
        "administradores": administradores
    }

    return render_template(
        "painel-adm.html",
        usuarios=usuarios,
        estatisticas=estatisticas
    )


@app.route("/admin/criar-usuario", methods=["POST"])
@admin_required
def rota_criar_usuario_admin():

    nome = request.form.get("nome", "")
    email = request.form.get("email", "")
    senha = request.form.get("senha", "")
    funcao = request.form.get("funcao", "comum")

    try:

        criar_usuario(nome, email, senha, funcao=funcao)

        flash("Usuario criado com sucesso.", "success")

    except ValueError as erro:

        flash(str(erro), "error")

    return redirect(url_for("painel_admin"))


@app.route(
    "/admin/editar-usuario/<int:usuario_id>",
    methods=["GET", "POST"]
)
@admin_required
def rota_editar_usuario_admin(usuario_id):

    usuario = buscar_usuario_por_id(usuario_id)

    if usuario is None or usuario.get("excluido", False):
        abort(404)

    if request.method == "POST":

        nome = request.form.get("nome", "")
        email = request.form.get("email", "")
        senha = request.form.get("senha", "")
        nova_funcao = request.form.get("funcao", usuario["funcao"])

        arquivo_foto = request.files.get("foto_perfil")

        try:

            foto = None

            if arquivo_foto and arquivo_foto.filename:
                foto = salvar_foto_perfil(arquivo_foto)

            editar_usuario(
                usuario_id,
                nome,
                email,
                senha,
                foto_perfil=foto
            )

            alterar_funcao_usuario(
                usuario_id,
                nova_funcao,
                session["user_id"]
            )

            flash("Usuario atualizado com sucesso.", "success")

            return redirect(url_for("painel_admin"))

        except ValueError as erro:

            usuario = buscar_usuario_por_id(usuario_id)

            return render_template(
                "edit-user.html",
                usuario=usuario,
                mensagem_erro=str(erro),
                admin_editando=True
            )

    return render_template(
        "edit-user.html",
        usuario=usuario,
        admin_editando=True
    )


@app.route(
    "/admin/excluir-usuario/<int:usuario_id>",
    methods=["POST"]
)
@admin_required
def rota_excluir_usuario(usuario_id):

    if session["user_id"] == usuario_id:

        flash(
            "Use a opcao de desativar propria conta para encerrar sua conta.",
            "error"
        )

        return redirect(url_for("painel_admin"))

    try:

        if excluir_usuario(usuario_id):
            flash("Usuario desativado com sucesso.", "success")
        else:
            flash("Usuario nao encontrado ou ja desativado.", "error")

    except ValueError as erro:

        flash(str(erro), "error")

    return redirect(url_for("painel_admin"))


@app.route(
    "/admin/reativar-usuario/<int:usuario_id>",
    methods=["POST"]
)
@admin_required
def rota_reativar_usuario(usuario_id):

    if reativar_usuario(usuario_id):
        flash("Usuario reativado com sucesso.", "success")
    else:
        flash("Usuario nao encontrado ou ja esta ativo.", "error")

    return redirect(url_for("painel_admin"))


# ============================================================
# ROTAS DE EXEMPLO DO PROJETO
# ============================================================

@app.route("/math/<op>/<a>/<b>")
def math(op, a, b):

    try:
        a = float(a)
        b = float(b)

    except ValueError:
        abort(400)

    if op == "soma":

        resultado = a + b
        nome_operacao = "Soma"
        simbolo = "+"

    elif op == "subtracao":

        resultado = a - b
        nome_operacao = "Subtracao"
        simbolo = "-"

    elif op == "multiplicacao":

        resultado = a * b
        nome_operacao = "Multiplicacao"
        simbolo = "x"

    elif op == "divisao":

        nome_operacao = "Divisao"
        simbolo = "÷"

        if b == 0:
            resultado = "Nao e possivel dividir por zero."
        else:
            resultado = a / b

    else:
        return "Operacao invalida.", 400

    return render_template(
        "math.html",
        a=a,
        b=b,
        resultado=resultado,
        nome_operacao=nome_operacao,
        simbolo=simbolo
    )


@app.route("/imc/<peso>/<altura>")
def imc(peso, altura):

    try:
        peso = float(peso)
        altura = float(altura)

    except ValueError:
        abort(400)

    if peso <= 0 or altura <= 0:
        abort(400)

    idade = request.args.get("idade", type=int)
    sexo = request.args.get("sexo")

    imc_calculado = peso / (altura ** 2)

    peso_minimo = 18.5 * (altura ** 2)
    peso_maximo = 24.9 * (altura ** 2)
    peso_sobrepeso = 25 * (altura ** 2)
    peso_obesidade = 30 * (altura ** 2)

    if imc_calculado < 18.5:
        classificacao = "Abaixo do peso"

    elif imc_calculado < 25:
        classificacao = "Normal"

    elif imc_calculado < 30:
        classificacao = "Sobrepeso"

    else:
        classificacao = "Obesidade"

    imc_minimo_barra = 15
    imc_maximo_barra = 35

    if imc_calculado <= imc_minimo_barra:
        posicao_barra = 0

    elif imc_calculado >= imc_maximo_barra:
        posicao_barra = 100

    else:
        posicao_barra = (
            (imc_calculado - imc_minimo_barra)
            / (imc_maximo_barra - imc_minimo_barra)
        ) * 100

    percentual_gordura = None
    classificacao_gordura = None

    if idade is not None and sexo in ("masculino", "feminino"):

        if sexo == "masculino":

            percentual_gordura = (
                1.20 * imc_calculado + 0.23 * idade - 16.2
            )

        else:

            percentual_gordura = (
                1.20 * imc_calculado + 0.23 * idade - 5.4
            )

    if percentual_gordura is not None:

        if sexo == "masculino":

            if percentual_gordura < 6:
                classificacao_gordura = "Essencial"

            elif percentual_gordura < 14:
                classificacao_gordura = "Atletico"

            elif percentual_gordura < 18:
                classificacao_gordura = "Fitness"

            elif percentual_gordura < 25:
                classificacao_gordura = "Aceitavel"

            else:
                classificacao_gordura = "Acima da faixa de referencia"

        else:

            if percentual_gordura < 14:
                classificacao_gordura = "Essencial"

            elif percentual_gordura < 21:
                classificacao_gordura = "Atletico"

            elif percentual_gordura < 25:
                classificacao_gordura = "Fitness"

            elif percentual_gordura < 32:
                classificacao_gordura = "Aceitavel"

            else:
                classificacao_gordura = "Acima da faixa de referencia"

    recomendacoes = {

        "Abaixo do peso": (
            "Os resultados de IMC sao apenas indicadores gerais. "
            "Procure orientacao de um profissional de saude para "
            "interpretar seus dados individualmente."
        ),

        "Normal": (
            "O IMC e um indicador geral e nao substitui uma avaliacao "
            "individual feita por um profissional de saude."
        ),

        "Sobrepeso": (
            "O IMC isolado nao determina o estado de saude. "
            "Uma avaliacao profissional considera outros fatores."
        ),

        "Obesidade": (
            "O IMC isolado nao estabelece um diagnostico. "
            "Procure orientacao profissional para uma avaliacao individual."
        )

    }

    recomendacao = recomendacoes[classificacao]

    # salva os dados do IMC na conta do usario conectado
    usuario_id = session.get("user_id")

    if usuario_id is not None:
        usuarios = carregar_usuarios()

        usuario = next(
            (
                u for u in usuarios
                if u.get("id") == usuario_id
                and not u.get("excluido", False)
            ),
            None
        )

        if usuario is not None:
            usuario["dados_imc"] = {
                "peso": peso,
                "altura": altura,
                "idade": idade,
                "sexo": sexo,
                "imc": round(imc_calculado, 2),
                "classificacao": classificacao,
                "data_calculo": datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                )
            }

            salvar_usuarios(usuarios)

    return render_template(
        "imc.html",
        peso=peso,
        altura=altura,
        idade=idade,
        sexo=sexo,
        imc=imc_calculado,
        classificacao=classificacao,
        peso_minimo=peso_minimo,
        peso_maximo=peso_maximo,
        peso_sobrepeso=peso_sobrepeso,
        peso_obesidade=peso_obesidade,
        posicao_barra=posicao_barra,
        percentual_gordura=percentual_gordura,
        classificacao_gordura=classificacao_gordura,
        recomendacao=recomendacao
    )


@app.route("/imc-novo")
def imc_novo():

    peso = request.args.get("peso")
    altura = request.args.get("altura")
    idade = request.args.get("idade")
    sexo = request.args.get("sexo")

    if not peso or not altura:
        abort(400)

    return redirect(
        url_for(
            "imc",
            peso=peso,
            altura=altura,
            idade=idade,
            sexo=sexo
        )
    )


# ============================================================
# EXECUCAO
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
