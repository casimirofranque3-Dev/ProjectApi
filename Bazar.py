from fastapi import FastAPI

app = FastAPI()

# rota inicial
@app.get("/")
def home():
    return {"mensagem": "API funcionando 🚀"}