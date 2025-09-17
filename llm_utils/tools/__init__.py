# DataHub 의존성을 선택적으로 만들기
try:
    from .datahub import (
        set_gms_server,
        get_info_from_db,
        get_metadata_from_db,
    )
    DATAHUB_AVAILABLE = True
except ImportError:
    # DataHub 없이도 작동하도록 더미 함수 제공
    DATAHUB_AVAILABLE = False
    
    def set_gms_server(gms_server: str):
        raise ImportError("DataHub 패키지가 설치되지 않았습니다. DataHub 기능을 사용하려면 'pip install datahub'를 실행하세요.")
    
    def get_info_from_db(max_workers: int = 8):
        raise ImportError("DataHub 패키지가 설치되지 않았습니다. FAISS 인덱스를 미리 생성하거나 'pip install datahub'를 실행하세요.")
    
    def get_metadata_from_db():
        raise ImportError("DataHub 패키지가 설치되지 않았습니다. DataHub 기능을 사용하려면 'pip install datahub'를 실행하세요.")

__all__ = [
    "set_gms_server",
    "get_info_from_db", 
    "get_metadata_from_db",
    "DATAHUB_AVAILABLE",
]