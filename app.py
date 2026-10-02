from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def inicio():
    return render_template("index.html")

@app.route("/sobre")
def sobre():
    return render_template("about.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/perfil")
def perfil():
    return render_template("profile.html")

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

    imc_calculado = peso / (altura **2)
    peso_minimo = 18.5 * (altura **2)
    peso_maximo = 24.9 * (altura **2)


    if imc_calculado < 18.5:
        classificacao = "Magreza"

    elif imc_calculado < 25:
        classificacao = "Normal"

    elif imc_calculado <30:
        classificacao = "Sobrepeso"

    else:
        classificacao = "Obesidade"

    return render_template(
        "imc.html",
        peso=peso,
        altura=altura,
        imc = imc_calculado,
        classificacao = classificacao,
        peso_minimo = peso_minimo,
        peso_maximo= peso_maximo
    )

if __name__ == "__main__":
    app.run(debug=True)