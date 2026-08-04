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



class UpdateBiografia(BaseModel):
	texto: str
	


class Post_User(BaseModel):
	product: str
	price: float
	description: str
	categoria: str
	visibilidade: str
	provinceSelected: list[str]
	checkbox: str
	user_id: str
	bairro: str
	
class CommentRequest(BaseModel):
	texto: str
	user_id: str
	post_id: str
	actor_id: str

class Followers(BaseModel):
	user_id: str
	ator_id: str

class UserFeed(BaseModel):
	user_id: str
	categoria: str

class Categorie(BaseModel):
	user_id: str
	
resend.api_key = "re_XnkgomgH_J3X1Zm7vHQPzS74cRa8Gwg71"

def enviar_email(email, codigo):
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": email,
        "subject": "Seu código OTP",
        "html": f"<strong>Seu código é: {codigo}</strong>"
    })

client = meilisearch.Client(
    "https://meilisearch-vb74.onrender.com", "minha_chave_super_secreta_123"
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
            "user_id": req.user_id,
            "product": req.product,
            "price": req.price,
            "description": req.description,
            "categoria": req.categoria,
            "visibilidade": req.visibilidade,
            "provincias": req.provinceSelected,
            "bairro": req.bairro,
            "comments_count": 0
        })
        
        db.collection("user_categories").document(req.user_id).set({
            "categorias": firestore.ArrayUnion([req.categoria])
        }, merge=True)
        

        client.index("user_posts").add_documents([
            {
                "id": post_id,
                "product": req.product
            }
        ])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

#Usuario deletando seu post
@app.post("/deletePost")
def Delete_Post(req: DeletePost):
	#Comentario tambem
	db.collection("user_posts").document(req.post_id).where("user_id", "==", req.user_id).delete()
	
	db.collection("user_posts").document(req.post_id).collection("comments").delete()



#Busncado nome da/s categorias criadas)
#user = ur
@app.post("/ur_name_categories")
def user_Categories(req: Categorie):
	doc = db.collection("user_categories").document(req.user_id).get()
	if not doc.exists:
		return {"categorias": []}
	return doc.to_dict()


#Post do próprio usuário, para tela Perfil
@app.post("/user_feed")
def user_Feed(req: UserFeed):
	docs = db.collection("user_posts").where("user_id", "==", req.user_id).where("categoria", "==", req.categoria).get()
	return {
	    "posts": [doc.to_dict() for doc in docs]
	}









#Criando Follwers  (seguir/seguindo)
@app.post("/followers")
def follwers(req:  Follwers):
		
		doc = db.collection("users").document(req.user_id).collection("followers").document(req.ator_id).get()
		
		if not doc.exists:
			follow = db.collection("users").document(req.user_id).collection("followers").document(req.ator_id).set({})
			
			db.collection("users").document(req.user_id).update({
			    "followers": firestore.Increment(1)
			})
			return {
			    "follow": True
			}
		
		else:
			doc.reference.delete()
			db.collection("users").document(req.user_id).update({
				    "followers": firestore.Increment(-1)
				})
			return {"follow": False}



#Pesquisando no MeiliSearch
@app.get("/search")
def search(q: str):
	result = client.index("user_posts").search(q)
	return result["hits"]


#Atualizando a Biografia
@app.post("/updateBiografia")
def Biografia(req: UpdateBiografia):
	db.collection("/users").document(req.user_id).update({
	    "biografia": req.texto
	})





#buscando post específico
@app.get("/posts/{id}")
def get_id_post(id: str):
	doc = db.collection("user_posts").document(id).get()
	if not doc.exists:
		raise HTTPException(status_code=404, detail="Post não encotrado")
	return doc.to_dict()






#PENDENTE
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
	    "texto": "o joão comentou no seu produto",
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
	

# Texte
@app.get("/")
def Msg():
	return {"Msg": "Rondando com sucesso!"}
