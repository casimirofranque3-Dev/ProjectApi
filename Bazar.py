from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth, firestore
import secrets
from datetime import datetime, timedelta, timezone
import resend
from fastapi.middleware.cors import CORSMiddleware
import uuid
import firebase_admin
from firebase_admin import credentials


if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
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
		
	
class UserNew(BaseModel):
	email: str

class Validar_UserNew(BaseModel):
	email: str
	senha: str
	nome: str
	provincia: str
	codigo: str

class Post_User(BaseModel):
	product: str
	price: float
	description: str
	categoria: str
	visibilidade: str
	provinceSelected: List[str]
	checkbox: str
	bairro: str
	
	
	
	
resend.api_key = "re_XnkgomgH_J3X1Zm7vHQPzS74cRa8Gwg71"

def enviar_email(email, codigo):
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": email,
        "subject": "Seu código OTP",
        "html": f"<strong>Seu código é: {codigo}</strong>"
    })




#No futuro.o uid tambem precisa ser salvo
@app.post("/post")
def Post(req: Post_User):
	try:
		
		post_id = str(uuid.uuid4())
		
		db.collection("user_posts").document(id).set({
		    "id": post_id,
	        "product": req.product,
	        "price": req.price,
	        "description": req.description,
	        "categoria": req.categoria,
	        "visibilidade": req.visibilidade,
	        "provincias": req.provinceSelected,
	        "bairro": req.bairro
	    })
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))




#AQUI
#Parte: 3   Novo Usuário  
#Enviar código para usuário Pendente
@app.post("/panding_user")
def panding_user(email: UserNew):
    try:
        
        codigo = str(secrets.randbelow(900000) + 100000)

        expira_em = datetime.utcnow() + timedelta(minutes=5)

        db.collection("Panding_User").document(email.email).set({
            "codigo": codigo,
            "TempoLimite": expira_em,
            "tentativas": 0
        })

        enviar_email(email.email, codigo)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"Msg": "O seu código foi enviado com sucesso!"}
	
	
	
	
	
	
	
#Parte: 3    Linha A
#validar Novo usuário
@app.post("/validarPanding_user")
def validar_userNew(req: Validar_UserNew):
    try:
        if not req.nome or not req.provincia or not req.senha or not req.email or not req.codigo:
            raise HTTPException(status_code=404, detail="Sem dados do Usuário")

        doc = db.collection("Panding_User").document(req.email).get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Usuário Não encontrado")

        dados = doc.to_dict()

        if datetime.now(timezone.utc) > dados["TempoLimite"]:
            raise HTTPException(status_code=400, detail="Tempo excedido")

        if dados.get("tentativas", 0) >= 3:
            raise HTTPException(status_code=403, detail="Número de tentativas excedido")

        if req.codigo != dados["codigo"]:
            db.collection("Panding_User").document(req.email).update({
                "tentativas": dados.get("tentativas", 0) + 1
            })

            raise HTTPException(status_code=400, detail="Código inválido")

        auth.create_user(
            email=req.email,
            password=req.senha
        )

        db.collection("Users").document(req.email).set({
            "nome": req.nome,
            "provincia": req.provincia
        })

        db.collection("Panding_User").document(req.email).delete()

        return {"user": "Conta criada com sucesso!"}

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
	
	
	
	
	
	

# Texte
@app.get("/")
def Msg():
	return {"Msg": "Rondando com sucesso!"}







#                          SENHA
#Parte: 2   Updating user Senha
#Gerando codigo e salvar no db
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




#                     SENHA
#Parte: 2  Linha A
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
        
        user = auth.get_user_by_email(req.email)
        
        auth.update_user(user.uid, password=req.novaSenha)
        
        db.collection("otps").document(req.email).delete()
        return {"msg": "senha alterada com sucesso!"}

    except HTTPException:
        raise
        
    except Exception as e:
    	raise HTTPException(status_code=500, detail=str(e))