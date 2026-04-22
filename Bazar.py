from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth, firestore
import secrets
from datetime import datetime, timedelta
import resend
from fastapi.middleware.cors import CORSMiddleware

cred = credentials.Certificate(
    {
  "type": "service_account",
  "project_id": "baza-13104",
  "private_key_id": "5bf9e81c4a1ec6d6b01446ed640d0ece387c7598",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDmqUUnRw4DycHR\nlDpoS2rvancWhBJemQnQ6cdXx5Zyt8hHJKididGna+khU+BUk58ljhHD0vjAHZmI\nbJx4SKFxQazLhiPqAXqSbmCd3DvD/1v623sO5ic8z/B6LnDGv4s91hrHJ6X9B7oq\nFh5wqVRwTQLWh5PvLUV+OC24OOL9pSEg1hiqommIcN71JmFh9y0oO/706WgqpNE8\nK2UK+DY0mKK3lwVBmLjoOTtcFui4+VINIdEV9YRZWBk8iHVELs48NKaZxXECCKGv\nA+ypfLecJ8YHlbSv4JSKpdQEOyLTgFp0IrkeOxriQVT+E8Xu0/VslMErCLix8mv9\nKkc3cms9AgMBAAECggEAZi55cJd1GW+A+Z+BKl+ynSIcZHCYlKiWJSLTSMsllmdd\nBUszmSqLInBXBAkcuUr2NxRTQV1ODglu0PVQcaa3Qi12Z2jisxD5pDHagkQkg8S1\nkhE12BlUK4fwf6fgFOOYwwl8rlodmdSY/3jx/jW9Lsym47OG8O8suGgZtOEaiYMM\nrUXeGat4IaB5lsXvO1sLYZm37ItBSUjhzbOZ7fu7bjXo6tL2Z1qiXwoUZtCInqzh\n9WUNDf/t33yWgWhCBpRlpr2n/Go/uvErQEKHzDJ/ohNtMSZtjuXgRKM3T9aeUAaq\npLoqkLxX9nXVStpkOws5tRCRu/3m8tjREsKaTFkcHwKBgQD31QIIICt0uUqCFD4b\nay/gkw/gSezNHVd16S1zFBgpW/rzBubL/qRtRW54o5VJNCBj0uNeQOBIuCyPGg+/\nKC1dSypDAa6fTp1l1yrVuVft6wgJ1YoeMu7L6tam49m/fj21Z9wrAggJ8xnOMgp5\nqfbnIEBq6g79wsftT7k0QJdqvwKBgQDuQ2Oyg1E7QwSZEOXAWwZJTR4alT/gn5B5\n8ELPbviNCdeasFLQ04ZNKgwXbc7HUxovUB29X1O5oYKI/ihsHxjPereubwlHPTot\n3iMPkaDnJ9TvxQJGRmKwQsT4YOVRMrr6eq3p5h8NeHcqc7QOctpFiv1x04QHEYob\nHJm8hTWVAwKBgDjXMuMYNb9MrAkPiXsSZ2WzdQW1DsmwfBnABDuLlUsPHIxWveJ1\nodKqBP9ITXn/qZobiShZ6tbi3t1nVcs69MSb87JwlVNWXYU5B0sDemZH7I0M2+O3\nPMuqLdcTFSL1WkPb8UQv8BYQGpAPLBXhZI53+C5NRmjvHpmQGmMgmVnTAoGBAK8A\nQFH1scxdRRtIFfha4xsj0WClDu3lRTDLD8dcMqMk/39W0v0e4B39LDRpKt+sYicu\nKSnWwqAtyLrmMrp3fLmn4RH17FKu3fSinA3rYMtnrjcN9MW5HPNpl1L3mHczU7J2\nORb7NwOl36EGqtGR+k/p7o2UVfz7HP0c3K5jCSARAoGBAK2VtTDgXCMGV7YCWtP3\ncVxu/NcmdfJw3M/O6xsrvypDwgsQajI5n3sUi2qRvJmIX76PR9T+kGUfotiOkpRY\nHZVzJZzHsgf5shLC1XInd+J9hlDU7f6I+FYAAl4lvc4rwn23heKqosMRW9WaxD49\nzIAWAAZvULxYY4KNQy9o3uCb\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@baza-13104.iam.gserviceaccount.com",
  "client_id": "101906284187167311618",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40baza-13104.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
)

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