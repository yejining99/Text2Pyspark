import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from llm_utils.vectordb import get_vector_db


def load_reranker_model(device: str = "cpu"):
    """한국어 reranker 모델을 로드하거나 다운로드합니다."""
    local_model_path = os.path.join(os.getcwd(), "ko_reranker_local")

    # 로컬에 저장된 모델이 있으면 불러오고, 없으면 다운로드 후 저장
    if os.path.exists(local_model_path) and os.path.isdir(local_model_path):
        print("🔄 ko-reranker 모델 로컬에서 로드 중...")
    else:
        print("⬇️ ko-reranker 모델 다운로드 및 저장 중...")
        model = AutoModelForSequenceClassification.from_pretrained(
            "Dongjin-kr/ko-reranker"
        )
        tokenizer = AutoTokenizer.from_pretrained("Dongjin-kr/ko-reranker")
        model.save_pretrained(local_model_path)
        tokenizer.save_pretrained(local_model_path)

    return HuggingFaceCrossEncoder(
        model_name=local_model_path,
        model_kwargs={"device": device},
    )


def get_retriever(retriever_name: str = "기본", top_n: int = 5, device: str = "cpu"):
    """검색기 타입에 따라 적절한 검색기를 생성합니다.

    Args:
        retriever_name: 사용할 검색기 이름 ("기본", "재순위", 등)
        top_n: 반환할 상위 결과 개수
    """
    print(device)
    retrievers = {
        "기본": lambda: get_vector_db().as_retriever(search_kwargs={"k": top_n}),
        "Reranker": lambda: ContextualCompressionRetriever(
            base_compressor=CrossEncoderReranker(
                model=load_reranker_model(device), top_n=top_n
            ),
            base_retriever=get_vector_db().as_retriever(search_kwargs={"k": top_n}),
        ),
    }

    if retriever_name not in retrievers:
        print(
            f"경고: '{retriever_name}' 검색기를 찾을 수 없습니다. 기본 검색기를 사용합니다."
        )
        retriever_name = "기본"

    return retrievers[retriever_name]()


def search_tables(
    query: str, retriever_name: str = "기본", top_n: int = 5, device: str = "cpu"
):
    """쿼리에 맞는 테이블 정보를 검색합니다."""
    print(f"🔍 검색 시작: '{query}' (retriever: {retriever_name}, top_n: {top_n})")
    
    try:
        if retriever_name == "기본":
            db = get_vector_db()
            print(f"✅ 벡터 DB 로드 성공")
            
            # similarity_search_with_score를 사용하여 유사도 점수도 함께 가져옴
            doc_score_pairs = db.similarity_search_with_score(query, k=top_n)
            doc_res = [(doc, score) for doc, score in doc_score_pairs]
            print(f"📊 검색 결과: {len(doc_res)}개 문서 찾음")
        else:
            retriever = get_retriever(
                retriever_name=retriever_name, top_n=top_n, device=device
            )
            docs = retriever.invoke(query)
            # Reranker의 경우 score 정보가 없으므로 기본값 설정
            doc_res = [(doc, getattr(doc, 'metadata', {}).get('score', 0.5)) for doc in docs]
            print(f"📊 Reranker 검색 결과: {len(doc_res)}개 문서 찾음")

        # 결과를 사전 형태로 변환
        documents_dict = {}
        for i, (doc, score) in enumerate(doc_res):
            try:
                lines = doc.page_content.split("\n")
                print(f"📄 처리 중인 문서 {i+1}: {lines[0][:50]}...")

                # 테이블명 및 설명 추출
                if ": " not in lines[0]:
                    print(f"⚠️ 경고: 테이블 정보 형식이 올바르지 않습니다: {lines[0]}")
                    continue
                    
                table_name, table_desc = lines[0].split(": ", 1)

                # 섹션별로 정보 추출 (테이블/컬럼만 사용)
                columns = {}
                current_section = None

                for j, line in enumerate(lines[1:], 1):
                    line = line.strip()

                    # 섹션 헤더 확인
                    if line == "Columns:":
                        current_section = "columns"
                        continue

                    # 각 섹션의 내용 파싱
                    if current_section == "columns" and ": " in line:
                        col_name, col_desc = line.split(": ", 1)
                        columns[col_name.strip()] = col_desc.strip()

                # 딕셔너리 저장 (유사도 점수 포함)
                documents_dict[table_name] = {
                    "table_description": table_desc.strip(),
                    "score": f"{score:.3f}",  # 유사도 점수 추가
                    "rank": i + 1,  # 순위 추가
                    **columns,  # 컬럼 정보 추가
                }
                print(f"✅ 테이블 '{table_name}' 처리 완료 (유사도: {score:.3f})")
                
            except Exception as e:
                print(f"❌ 문서 처리 중 오류 발생: {e}")
                print(f"문제가 된 문서: {doc.page_content[:100]}...")
                continue

        print(f"🎯 최종 결과: {len(documents_dict)}개 테이블 반환")
        return documents_dict
        
    except Exception as e:
        print(f"❌ 검색 중 전체 오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {}
