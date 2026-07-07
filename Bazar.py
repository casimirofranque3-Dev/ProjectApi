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
import meilisearch



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
	provinceSelected: list[str]
	checkbox: str
	bairro: str
	
class CommentRequest(BaseModel):
	texto: str
	user_id: str
	post_id: str
	actor_id: str	
	
	
resend.api_key = "re_XnkgomgH_J3X1Zm7vHQPzS74cRa8Gwg71"

def enviar_email(email, codigo):
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": email,
        "subject": "Seu código OTP",
        "html": f"<strong>Seu código é: {codigo}</strong>"
    })

client = meilisearch.Client(
    "https://meilisearch-vb74.onrender.com", "minha_chave_super_reta_123"
)

@app.get("/meili")
def teste():
	return client.health()



#Criando Post. No futuro.o uid tambem precisa ser salvo
@app.post("/post")
def Criar_post(req: Post_User):
	try:
		
		post_id = str(uuid.uuid4())
		
		db.collection("user_posts").document(post_id).set({
		    "id": post_id,
	        "product": req.product,
	        "price": req.price,
	        "description": req.description,
	        "categoria": req.categoria,
	        "visibilidade": req.visibilidade,
	        "provincias": req.provinceSelected,
	        "bairro": req.bairro,
	        "comments_count": 0
	    })
	    
	    client.index("user_posts").add_documents([
	        {
	            "id": post_id,
	            "product": req.product
	        }
	    ])
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

#Pesquisando no MeiliSearch

@app.get("/search")
def search(q: str):
	result = client.index("user_posts").search(q)
	return result["hits"]

#buscando post específico
@app.get("/posts/{id}")
def get_id_post(id: str):
	doc = db.collection("user_posts").document(id).get()
	if not doc.exists:
		raise HTTPException(status_code=404, detail="Post não encotrado")
	return doc.to_dict()


#criando comentários e notificação
@app.post("/post/{post_id}/comment")
def criar_comentario(post_id: str, req: CommentRequest):
	
	comment_id = str(uuid.uuid4())
	
	db.collection("user_posts").document(post_id).collection("comments").document(comment_id).set({
	    "texto": req.texto,
	    "criado_em": firestore.SERVER_TIMESTAMP
	})
	
	db.collection("user_posts").document(post_id).update({
	    "comments_count": firestore.Increment(1)
	})
	
	notification_id = str(uuid.uuid4())
	
	db.collection("notifications").document(notification_id).set({
	    "user_id": req.user_id,
	    "notification_id": notification_id,
	    "actor_id": req.actor_id,
	    "post_id": req.post_id,
	    "texto": "o jaoo comentou no seu produto",
	    "lida": False,
	    "criado_em": firestore.SERVER_TIMESTAMP
	})


#buscando comentários pelo id do post
@app.get("/post/{post_id}/comment")
def get_comments(post_id: str):
	
	comments = db.collection("user_posts").document(post_id).collection("comments").get()
	
	return {"comments": [comment.to_dict() for comment in comments]}


#buscando posts
@app.get("/posts")
def getPost():
	posts = db.collection("user_posts").get()
	return {"posts": [post.to_dict() for post in posts]}




#Buscando as notificações
@app.get("/notifications/{user_id}")
def get_notification(user_id: str):
	notifications = ( db.collection("notifications").where("user_id", "==", user_id).get()
	)
	return {"notifications": [notification.to_dict() for notification in notifications]}


#Marcar Notificação como lida e depois apagar
@app.post("/notifications{notification_id}/read")
def read_notification(notification: str):
	db.collection("notifications").document(notification_id).update({
	    "lida": True
	})

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