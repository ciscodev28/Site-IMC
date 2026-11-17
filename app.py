
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps
import json
import os

app = Flask(__name__)

# Carregar variáveis do arquivo .env
load_dotenv()

# Chave secreta para assinatura das sessões
app.secret_key = os.getenv("SECRET_KEY")

# Caminho do banco de dados
DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "database.json"
)


def inicializar_banco():

    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    if not os.path.exists(DATABASE):
        with open(DATABASE, "w", encoding="utf-8") as arquivo:
            json.dump([], arquivo, ensure_ascii=False, indent=4)


inicializar_banco()


def carregar_usuarios():
    with open(DATABASE, "r", encoding="utf-8") as arquivo:
        usuarios = json.load(arquivo)

    return usuarios


def salvar_usuarios(usuarios):

    with open(DATABASE, "w", encoding="utf-8") as arquivo:
        json.dump(
            usuarios,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


# Promover usuário para administrador
def promover_admin(usuario_id):

    usuarios = carregar_usuarios()

    for usuario in usuarios:

        if usuario["id"] == usuario_id and not usuario["excluido"]:
            usuario["funcao"] = "admin"

            salvar_usuarios(usuarios)

            return True

    return False


# Excluir usuário logicamente
def excluir_usuario(usuario_id):

    usuarios = carregar_usuarios()

    for usuario in usuarios:

        if usuario["id"] == usuario_id and not usuario["excluido"]:

            usuario["excluido"] = True

            salvar_usuarios(usuarios)

            return True

    return False


# Cadastrar novo usuário
def criar_usuario(nome, email, senha):

    usuarios = carregar_usuarios()

    nome = nome.strip()
    email = email.strip().lower()

    if not nome or not email or not senha:
        raise ValueError("Todos os campos são obrigatórios.")

    for usuario in usuarios:

        if usuario["email"].lower() == email:
            raise ValueError("Este e-mail já está cadastrado.")

    if usuarios:
        novo_id = max(usuario["id"] for usuario in usuarios) + 1
    else:
        novo_id = 1

    novo_usuario = {
        "id": novo_id,
        "nome": nome,
        "email": email,
        "senha_hash": generate_password_hash(
            senha,
            method="pbkdf2:sha256"
        ),
        "foto_perfil": None,
        "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "funcao": "comum",
        "excluido": False
    }

    usuarios.append(novo_usuario)

    salvar_usuarios(usuarios)

    return novo_usuario


# Proteger rotas que exigem autenticação
def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "usuario_id" not in session:
            flash("Faça login para acessar esta página.", "error")
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# Verificar se o usuário possui permissão de administrador
def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "usuario_id" not in session:
            flash("Faça login para acessar esta página.", "error")
            return redirect(url_for("login"))

        usuarios = carregar_usuarios()

        usuario_atual = next(
            (
                usuario for usuario in usuarios
                if usuario["id"] == session["usuario_id"]
                and not usuario["excluido"]
            ),
            None
        )

        if usuario_atual is None:
            session.clear()
            flash("Sua sessão não é mais válida. Faça login novamente.", "error")
            return redirect(url_for("login"))

        if usuario_atual["funcao"] != "admin":
            flash("Você não tem permissão para acessar esta página.", "error")
            return redirect(url_for("perfil"))

        return f(*args, **kwargs)

    return decorated_function


# Rota temporária para testar a proteção administrativa
@app.route("/teste-admin")
@admin_required
def teste_admin():
    return "Acesso permitido: administrador!"


# Rota de exclusão de usuários
@app.route("/admin/excluir-usuario/<int:usuario_id>", methods=["POST"])
@admin_required
def rota_excluir_usuario(usuario_id):

    # Impedir que o administrador exclua a própria conta
    if session.get("usuario_id") == usuario_id:
        flash("Você não pode excluir sua própria conta.", "error")
        return redirect(url_for("perfil"))

    if excluir_usuario(usuario_id):
        flash("Usuário excluído com sucesso.", "success")
    else:
        flash("Usuário não encontrado ou já excluído.", "error")

    return redirect(url_for("perfil"))


# Rota de cadastro
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        nome = request.form.get("nome", "")
        email = request.form.get("email", "")
        senha = request.form.get("senha", "")

        try:
            criar_usuario(nome, email, senha)

            flash("Cadastro realizado com sucesso!", "success")

            return redirect(url_for("login"))

        except ValueError as erro:
            return render_template(
                "register.html",
                mensagem_erro=str(erro)
            )

    return render_template("register.html")


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/sobre")
def sobre():
    return render_template("about.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        usuarios = carregar_usuarios()

        usuario_encontrado = None

        for usuario in usuarios:

            if usuario["email"].lower() == email:
                usuario_encontrado = usuario
                break

        if usuario_encontrado is None or usuario_encontrado["excluido"]:
            flash("E-mail ou senha incorretos.", "error")
            return redirect(url_for("login"))

        if check_password_hash(
            usuario_encontrado["senha_hash"],
            senha
        ):

            session.clear()

            session["usuario_id"] = usuario_encontrado["id"]
            session["usuario_nome"] = usuario_encontrado["nome"]
            session["usuario_funcao"] = usuario_encontrado["funcao"]

            flash("Login realizado com sucesso!", "success")

            return redirect(url_for("perfil"))

        else:
            flash("E-mail ou senha incorretos.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


# Encerrar sessão
@app.route("/logout")
def logout():

    session.clear()

    flash("Você saiu da sua conta.", "success")

    return redirect(url_for("login"))


@app.route("/profile")
@login_required
def perfil():

    usuarios = carregar_usuarios()

    usuario_atual = next(
        (
            usuario for usuario in usuarios
            if usuario["id"] == session["usuario_id"]
            and not usuario["excluido"]
        ),
        None
    )

    if usuario_atual is None:
        session.clear()
        flash("Sua sessão não é mais válida. Faça login novamente.", "error")
        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        nome=usuario_atual["nome"],
        email=usuario_atual["email"]
    )


@app.route("/math/<op>/<a>/<b>")
def math(op, a, b):

    a = float(a)
    b = float(b)

    if op == "soma":

        resultado = a + b
        nome_operacao = "Soma"
        simbolo = "+"

    elif op == "subtracao":

        resultado = a - b
        nome_operacao = "Subtração"
        simbolo = "-"

    elif op == "multiplicacao":

        resultado = a * b
        nome_operacao = "Multiplicação"
        simbolo = "x"

    elif op == "divisao":

        nome_operacao = "Divisão"
        simbolo = "÷"

        if b == 0:
            resultado = "Não é possível dividir por zero."
        else:
            resultado = a / b

    else:
        return "Operação inválida."

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

    peso = float(peso)
    altura = float(altura)

    idade = request.args.get("idade", type=int)
    sexo = request.args.get("sexo")

    # Cálculo do IMC
    imc_calculado = peso / (altura ** 2)

    # Faixas de peso
    peso_minimo = 18.5 * (altura ** 2)
    peso_maximo = 24.9 * (altura ** 2)
    peso_sobrepeso = 25 * (altura ** 2)
    peso_obesidade = 30 * (altura ** 2)

    # Classificação do IMC
    if imc_calculado < 18.5:
        classificacao = "Abaixo do peso"

    elif imc_calculado < 25:
        classificacao = "Normal"

    elif imc_calculado < 30:
        classificacao = "Sobrepeso"

    else:
        classificacao = "Obesidade"

    # Posição da bolinha
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

    # Gordura corporal
    percentual_gordura = None
    classificacao_gordura = None

    if idade is not None and sexo in ["masculino", "feminino"]:

        if sexo == "masculino":
            percentual_gordura = (
                1.20 * imc_calculado
                + 0.23 * idade
                - 16.2
            )

        else:
            percentual_gordura = (
                1.20 * imc_calculado
                + 0.23 * idade
                - 5.4
            )

    # Classificação da gordura
    if percentual_gordura is not None:

        if sexo == "masculino":

            if percentual_gordura < 6:
                classificacao_gordura = "Essencial"

            elif percentual_gordura < 14:
                classificacao_gordura = "Atlético"

            elif percentual_gordura < 18:
                classificacao_gordura = "Fitness"

            elif percentual_gordura < 25:
                classificacao_gordura = "Aceitável"

            else:
                classificacao_gordura = "Obesidade"

        else:

            if percentual_gordura < 14:
                classificacao_gordura = "Essencial"

            elif percentual_gordura < 21:
                classificacao_gordura = "Atlético"

            elif percentual_gordura < 25:
                classificacao_gordura = "Fitness"

            elif percentual_gordura < 32:
                classificacao_gordura = "Aceitável"

            else:
                classificacao_gordura = "Obesidade"

    # Recomendação
    if classificacao == "Abaixo do peso":

        recomendacao = (
            "Para esta classificação, o projeto recomenda: "
            "atenção aos hábitos de saúde e acompanhamento profissional."
        )

    elif classificacao == "Normal":

        recomendacao = (
            "Mantenha hábitos de vida saudáveis e acompanhe "
            "regularmente seus indicadores de saúde."
        )

    elif classificacao == "Sobrepeso":

        recomendacao = (
            "É recomendado observar os hábitos de saúde e, "
            "quando necessário, buscar orientação profissional."
        )

    else:

        recomendacao = (
            "É recomendado buscar orientação de um profissional "
            "de saúde para uma avaliação individualizada."
        )

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

    return redirect(
        url_for(
            "imc",
            peso=peso,
            altura=altura,
            idade=idade,
            sexo=sexo
        )
    )

if __name__ == "__main__":
    app.run(debug=True)