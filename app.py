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
if __name__ == "__main__":
    app.run(debug=True)