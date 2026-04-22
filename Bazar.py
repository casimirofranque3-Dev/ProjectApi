from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth, firestore
import secrets
from datetime import datetime, timedelta
import resend
from fastapi.middleware.cors import CORSMiddleware

cred = credentials.Certificate("serviceAccount.json")


firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pode restringir depois
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EmailRequest(BaseModel):
	email: str
	
class SenhaNew(BaseModel):
	novaSenha: str
	email: str
	
class CodigoRequest(BaseModel):
	codigo: str
	email: str



resend.api_key = "re_XnkgomgH_J3X1Zm7vHQPzS74cRa8Gwg71"

def enviar_email(email, codigo):
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": email,
        "subject": "Seu código OTP",
        "html": f"<strong>Seu código é: {codigo}</strong>"
    })


@app.get("/")
def Msg():
	return {"Msg": "Rondando com sucesso!"}

@app.post("/verifying_userCode")
def verify_user(req: EmailRequest):
	try:
		user = auth.get_user_by_email(req.email)
		
		codigo = str(secrets.randbelow(900000) + 100000)
		
		expira_em = datetime.utcnow() + timedelta(minutes=5)
		
		db.collection("otps").document(req.email).set({
		    "codigo": codigo,
		    "validade": expira_em,
		    "tentativas": 0
		})
		
		enviar_email(req.email, codigo)
	
	except auth.UserNotFoundError:
		raise HTTPException(status_code=404, detail="Usuário não encontrado")
		
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
	return{"Msg": "Código enviado com sucesso"}




#validar: codigo e tempo
@app.post("/validar")
def validar(req: CodigoRequest):
    try:
        doc = db.collection("otps").document(req.email).get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Dados não encontrado")

        dados = doc.to_dict()

        if datetime.utcnow() > dados["validade"]:
            raise HTTPException(status_code=400, detail="Tempo excedido")

        if dados.get("tentativas", 0) >= 3:
            raise HTTPException(status_code=403, detail="Número de tentativas excedido")

        if req.codigo != dados["codigo"]:
            db.collection("otps").document(req.email).update({
                "tentativas": dados.get("tentativas", 0) + 1
            })
            raise HTTPException(status_code=400, detail="Código inválido")

        return {"Msg": "Codigo correto"}

    except Exception as e:
        return {
            "erro": str(e)
        }




#Atualizando a senha nova
@app.post("/updateSenha")
def NewSenha(req: SenhaNew):
	try:
		user = auth.get_user_by_email(req.email)
		
		auth.update_user(user.uid, password=req.novaSenha)
		
		db.collection("otps").document(req.email).delete()
		
	except Exception:
		raise HTTPException(status_code=500, detail="Erro ao atualizar a senha.")	