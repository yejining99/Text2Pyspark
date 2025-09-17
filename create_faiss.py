"""
create_faiss.py

CSV 파일에서 테이블과 컬럼 정보를 불러와 OpenAI 임베딩으로 벡터화한 뒤,
FAISS 인덱스를 생성하고 로컬 디렉토리에 저장한다.

환경 변수:
    OPEN_AI_KEY: OpenAI API 키
    OPEN_AI_EMBEDDING_MODEL: 사용할 임베딩 모델 이름

출력:
    지정된 OUTPUT_DIR 경로에 FAISS 인덱스 저장
"""

import csv
import os
from collections import defaultdict

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()
CSV_PATH = "./table_catalog.csv"  # 위 CSV 파일 경로
OUTPUT_DIR = "./table_info_db"    # .env 파일의 VECTORDB_LOCATION 값과 동일하게 맞추세요.

tables = defaultdict(lambda: {"desc": "", "columns": []})
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:  # BOM 처리를 위해 utf-8-sig 사용
    reader = csv.DictReader(f)
    for row in reader:
        t = row["table_name"].strip()
        tables[t]["desc"] = row["table_description"].strip()
        col = row["column_name"].strip()
        col_desc = row["column_description"].strip()
        tables[t]["columns"].append((col, col_desc))

docs = []
for t, info in tables.items():
    cols = "\n".join([f"{c}: {d}" for c, d in info["columns"]])
    page = f"{t}: {info['desc']}\nColumns:\n {cols}"
    from langchain.schema import Document

    docs.append(Document(page_content=page))

emb = OpenAIEmbeddings(
    model=os.getenv("OPEN_AI_EMBEDDING_MODEL"), openai_api_key=os.getenv("OPEN_AI_KEY")
)
db = FAISS.from_documents(docs, emb)
os.makedirs(OUTPUT_DIR, exist_ok=True)
db.save_local(OUTPUT_DIR)
print(f"FAISS index saved to: {OUTPUT_DIR}")