"""
VectorDB 팩토리 모듈 - 환경 변수에 따라 적절한 VectorDB 인스턴스를 생성
"""

import os
from typing import Optional

from llm_utils.vectordb.faiss_db import get_faiss_vector_db

# PGVector 관련 라이브러리 optional import
try:
    from llm_utils.vectordb.pgvector_db import get_pgvector_db
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    print("PGVector 관련 라이브러리가 설치되지 않았습니다. FAISS를 사용합니다.")


def get_vector_db(
    vectordb_type: Optional[str] = None, vectordb_location: Optional[str] = None
):
    """
    VectorDB 타입과 위치에 따라 적절한 VectorDB 인스턴스를 반환합니다.

    Args:
        vectordb_type: VectorDB 타입 ("faiss" 또는 "pgvector"). None인 경우 환경 변수에서 읽음.
        vectordb_location: VectorDB 위치 (FAISS: 디렉토리 경로, pgvector: 연결 문자열). None인 경우 환경 변수에서 읽음.

    Returns:
        VectorDB 인스턴스 (FAISS 또는 PGVector)
    """
    if vectordb_type is None:
        vectordb_type = os.getenv("VECTORDB_TYPE", "faiss").lower()

    if vectordb_location is None:
        vectordb_location = os.getenv("VECTORDB_LOCATION")

    if vectordb_type == "faiss":
        return get_faiss_vector_db(vectordb_location)
    elif vectordb_type == "pgvector":
        if PGVECTOR_AVAILABLE:
            return get_pgvector_db(vectordb_location)
        else:
            raise ImportError(
                "pgvector 관련 라이브러리가 설치되지 않았습니다. 'pip install pgvector langchain-postgres psycopg[binary]'를 실행하거나 'faiss'를 사용하세요."
            )
    else:
        raise ValueError(
            f"지원하지 않는 VectorDB 타입: {vectordb_type}. 'faiss' 또는 'pgvector'를 사용하세요."
        )
