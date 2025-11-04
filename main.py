from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import sqlite3
import io
import requests
import os

app = FastAPI()

# CORS liberado para o frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 Configure sua chave da OpenRouter aqui
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

# Criação do banco SQLite para histórico
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pergunta TEXT,
    resposta TEXT
)
""")
conn.commit()


@app.post("/analisar/")
async def analisar(file: UploadFile, pergunta: str = Form(...)):
    conteudo = await file.read()
    df = pd.read_csv(io.BytesIO(conteudo))

    resumo = df.describe(include='all').to_string()

    prompt = f"""
    Você é um analista de vendas da empresa Alpha Insights.
    Baseando-se nos seguintes dados de vendas:
    {resumo}

    Responda de forma clara e objetiva à pergunta: "{pergunta}".
    """

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-oss-20b:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
    )

    resposta_texto = response.json()["choices"][0]["message"]["content"]

    # salva no histórico
    cursor.execute("INSERT INTO historico (pergunta, resposta) VALUES (?, ?)", (pergunta, resposta_texto))
    conn.commit()

    return {"resposta": resposta_texto}


@app.get("/historico/")
async def historico():
    cursor.execute("SELECT * FROM historico ORDER BY id DESC LIMIT 20")
    dados = cursor.fetchall()
    return [{"id": r[0], "pergunta": r[1], "resposta": r[2]} for r in dados]
