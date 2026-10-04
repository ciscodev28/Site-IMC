from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route("/")
def inicio():
    return render_template("index.html")

@app.route("/sobre")
def sobre():
    return render_template("about.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        senha = request.form["senha"]

        if usuario == "admin" and senha == "1234":

            nome = request.form["nome"]
            email = request.form["email"]
            idade = request.form["idade"]
            sexo = request.form["sexo"]
            peso = request.form["peso"]
            altura = request.form["altura"]

            return redirect(
                url_for(
                    "perfil",
                    nome=nome,
                    email=email,
                    idade=idade,
                    peso=peso,
                    altura=altura,
                    sexo=sexo
                )
            )

        else:
            return "Usuário ou senha incorretos."

    return render_template("login.html")

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