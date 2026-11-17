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

# caminho do bando de dados
DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "database.json"
)

def inicializar_banco():

    #criar a pasta data caso não exista
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    if not os.path.exists(DATABASE):
        with open(DATABASE, "w", encoding="utf-8") as arquivo:
            json.dump([], arquivo, ensure_ascii=False, indent=4)

# executar inicialização
inicializar_banco()


def carregar_usuarios():
    with open(DATABASE, "r", encoding="utf-8")as arquivo:
        usuarios = json.load(arquivo)
    return usuarios 


# Salvar usuários no banco de dados
def salvar_usuarios(usuarios):

    with open(DATABASE, "w", encoding="utf-8") as arquivo:

        json.dump(
            usuarios,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


# Cadastrar novo usuário
def criar_usuario(nome, email, senha):

    usuarios = carregar_usuarios()

    # Limpar e padronizar os dados
    nome = nome.strip()
    email = email.strip().lower()

    # Verificar campos obrigatórios
    if not nome or not email or not senha:
        raise ValueError("Todos os campos são obrigatórios.")

    # Verificar se o e-mail já está cadastrado
    for usuario in usuarios:

        if usuario["email"].lower() == email:
            raise ValueError("Este e-mail já está cadastrado.")

    # Gerar ID automaticamente
    if usuarios:
        novo_id = max(usuario["id"] for usuario in usuarios) + 1
    else:
        novo_id = 1

    # Criar registro do usuário
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

    # Adicionar usuário à lista
    usuarios.append(novo_usuario)

    # Salvar alterações
    salvar_usuarios(usuarios)

    return novo_usuario

# rota de cadastro
@app.route("/cadastro", methods = ["GET", "POST"])
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
                mensagem_erro = str(erro)
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

        # procurar usuário pelo e-mail
        usuario_encontrado = None 
        
        for usuario in usuarios:

            if usuario ["email"].lower() == email:
                usuario_encontrado = usuario
                break

        # verificar se o usuário existe e não foi excluído 
        if usuario_encontrado is None or usuario_encontrado["excluido"]:
            flash("E-mail ou senha incorretos.", "error")
            return redirect(url_for("login"))

        # verificar a senha
        if check_password_hash(
            usuario_encontrado["senha_hash"],
            senha
        ):
           # criar sessão
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

# encerrar sessão
@app.route("/logout")
def logout():

    session.clear()

    flash("Você saiu da sua conta.", "success")

    return redirect(url_for("login"))

@app.route("/profile")
def perfil():

    nome = request.args.get("nome")
    email = request.args.get("email")
    idade = request.args.get("idade")
    peso = request.args.get("peso")
    altura = request.args.get("altura")
    sexo = request.args.get("sexo")

    return render_template(
        "profile.html",
        nome=nome,
        email=email,
        idade=idade,
        peso=peso,
        altura=altura,
        sexo=sexo
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

    # =========================
    # CÁLCULO DO IMC
    # =========================

    imc_calculado = peso / (altura ** 2)


    # =========================
    # FAIXAS DE PESO
    # =========================

    peso_minimo = 18.5 * (altura ** 2)
    peso_maximo = 24.9 * (altura ** 2)
    peso_sobrepeso = 25 * (altura ** 2)
    peso_obesidade = 30 * (altura ** 2)


    # =========================
    # CLASSIFICAÇÃO DO IMC
    # =========================

    if imc_calculado < 18.5:

        classificacao = "Abaixo do peso"

    elif imc_calculado < 25:

        classificacao = "Normal"

    elif imc_calculado < 30:

        classificacao = "Sobrepeso"

    else:

        classificacao = "Obesidade"


    # =========================
    # POSIÇÃO DA BOLINHA
    # =========================

    # A régua representa aproximadamente
    # IMC de 15 até 35

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


    # =========================
    # GORDURA CORPORAL
    # =========================

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


    # =========================
    # CLASSIFICAÇÃO DA GORDURA
    # =========================

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


    # =========================
    # RECOMENDAÇÃO
    # =========================

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


    # =========================
    # ENVIAR PARA O HTML
    # =========================

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