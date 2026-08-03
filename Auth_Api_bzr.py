from fastapi import FastAPI
from firebase_admin import credentials, auth, firestore
import secrets
import resend

if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pode restringir depois
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


db = firestore.client()

app = FastAPI()
    
    
    
class UserNew(BaseModel):
	email: str

class SenhaNew(BaseModel):
	novaSenha: str
	email: str

class CodigoRequest(BaseModel):
	codigoOtp: str
	email: str	
		
class EmailRequest(BaseModel):
	email: str
	email_new: str
	
class Validar_UserNew(BaseModel):
	email: str
	senha: str
	nome: str
	provincia: str
	codigo: str

class RequestDelete(BaseModel):
	email: str


resend.api_key = "re_XnkgomgH_J3X1Zm7vHQPzS74cRa8Gwg71"

def enviar_email(email, codigo):
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": email,
        "subject": "Seu código OTP",
        "html": f"<strong>Seu código é: {codigo}</strong>"
    })


#1
#AUTH:  CRIAR CONTA
#Parte: 1  Novo Usuário  Linha: A
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
    




#Parte: 1  Linha B
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

        db.collection("users").document(req.email).set({
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





#STEP: first
#UPDATE: SENHA
#info: verificar email e enviar o código
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


# STEP: first
#Lign: 2
#infor: verify se doc existe e validar tempo, codg e tentativas
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

        if req.codigoOtp != dados["codigo"]:
            db.collection("otps").document(req.email).update({
                "tentativas": dados.get("tentativas", 0) + 1
            })
            raise HTTPException(status_code=400, detail="Código inválido")

    except HTTPException:
        raise
        
    except Exception as e:
    	raise HTTPException(status_code=500, detail=str(e))
   



#STEP: first
#Lign: 3 last
#infor: verify se doc existe,  e tentativas, por último: Atualizar a senha 
@app.post("/updateSenha")
def validar(req: SenhaNew):
    try:
        doc = db.collection("otps").document(req.email).get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Dados não encontrado")

        dados = doc.to_dict()

        if dados.get("tentativas", 0) >= 3:
            raise HTTPException(status_code=403, detail="Número de tentativas excedido")

        
        user = auth.get_user_by_email(req.email)
        
        auth.update_user(user.uid, password=req.novaSenha)
        
        db.collection("otps").document(req.email).delete()
        return {"msg": "senha alterada com sucesso!"}

    except HTTPException:
        raise
        
    except Exception as e:
    	raise HTTPException(status_code=500, detail=str(e))
    	


	

@app.post("/updateEmail")
def UpdateEmail(req: EmailRequest):
	
	user = auth.get_user_by_email(req.email)
	auth.update_user(
	    user.uid,
	    email = req.email_new
	)
	

@app.post("/deleteAccount")
def Delete(req: RequestDelete):
	
	user = auth.get_user_by_email(req.email)
	auth.delete_user(
	    user.uid
	)