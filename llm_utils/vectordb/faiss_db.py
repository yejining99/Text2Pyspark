"""
FAISS VectorDB 구현
"""

import os
from langchain_community.vectorstores import FAISS
from typing import Optional

from llm_utils.llm import get_embeddings


def get_faiss_vector_db(vectordb_path: Optional[str] = None):
    """FAISS 벡터 데이터베이스를 로드하거나 생성합니다."""
    embeddings = get_embeddings()

    # 기본 경로 설정
    if vectordb_path is None:
        vectordb_path = os.path.join(os.getcwd(), "table_info_db")

    try:
        db = FAISS.load_local(
            vectordb_path,
            embeddings,
            allow_dangerous_deserialization=True,
        )
        print(f"기존 FAISS 인덱스를 로드했습니다: {vectordb_path}")
    except Exception as e:
        print(f"FAISS 인덱스 로드 실패: {e}")
        # DataHub 없이도 작동하도록 수정
        try:
            from llm_utils.tools import get_info_from_db
            documents = get_info_from_db()
            db = FAISS.from_documents(documents, embeddings)
            db.save_local(vectordb_path)
            print(f"DataHub에서 VectorDB를 새로 생성했습니다: {vectordb_path}")
        except ImportError:
            # DataHub가 없으면 에러 메시지와 함께 종료
            raise FileNotFoundError(
                f"FAISS 인덱스를 찾을 수 없습니다: {vectordb_path}\n"
                "해결 방법:\n"
                "1. create_faiss.py를 실행해서 FAISS 인덱스를 먼저 생성하세요\n"
                "2. 또는 DataHub를 설치하세요: pip install datahub==0.999.1"
            )
    return db