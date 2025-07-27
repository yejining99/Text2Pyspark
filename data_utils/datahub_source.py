from datahub.metadata.schema_classes import DatasetPropertiesClass, SchemaMetadataClass
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph
from datahub.metadata.schema_classes import UpstreamLineageClass
from collections import defaultdict
import requests
from data_utils.queries import (
    ROOT_GLOSSARY_NODES_QUERY,
    GLOSSARY_NODE_QUERY,
    LIST_QUERIES_QUERY,
    QUERIES_BY_URN_QUERY,
    GLOSSARY_TERMS_BY_URN_QUERY,
)


class DatahubMetadataFetcher:
    def __init__(self, gms_server="http://localhost:8080", extra_headers={}):
        # gms_server 주소 유효성 검사
        if not self._is_valid_gms_server(gms_server):
            raise ValueError(f"유효하지 않은 GMS 서버 주소: {gms_server}")

        self.emitter = DatahubRestEmitter(
            gms_server=gms_server, extra_headers=extra_headers
        )
        self.datahub_graph = self.emitter.to_graph()
        self.gms_server = gms_server

    def _is_valid_gms_server(self, gms_server):
        # GMS 서버 주소의 유효성을 검사하는 로직 추가
        # GraphQL 요청을 사용하여 서버 상태 확인
        query = {"query": "{ health { status } }"}
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                f"{gms_server}/api/graphql", json=query, headers=headers
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_urns(self):
        # 필터를 적용하여 데이터셋의 URN 가져오기
        return self.datahub_graph.get_urns_by_filter()

    def get_table_name(self, urn):
        # URN에 대한 테이블 이름 가져오기
        dataset_properties = self.datahub_graph.get_aspect(
            urn, aspect_type=DatasetPropertiesClass
        )
        if dataset_properties:
            database_info = dataset_properties.get("customProperties", {}).get(
                "dbt_unique_id", ""
            )
            if database_info:
                database_info = database_info.split(".")[-2]
            else:
                database_info = ""
            table_info = dataset_properties.get("name", None)
            return database_info + "." + table_info
        return None

    def get_table_description(self, urn):
        # URN에 대한 테이블 설명 가져오기
        dataset_properties = self.datahub_graph.get_aspect(
            urn, aspect_type=DatasetPropertiesClass
        )
        if dataset_properties:
            return dataset_properties.get("description", None)
        return None

    def get_column_names_and_descriptions(self, urn):
        # URN에 대한 컬럼 이름 및 설명 가져오기
        schema_metadata = self.datahub_graph.get_aspect(
            urn, aspect_type=SchemaMetadataClass
        )
        columns = []
        if schema_metadata:
            for field in schema_metadata.fields:

                # nativeDataType이 없거나 빈 문자열인 경우 None 처리
                native_type = getattr(field, "nativeDataType", None)
                column_type = (
                    native_type if native_type and native_type.strip() else None
                )

                columns.append(
                    {
                        "column_name": field.fieldPath,
                        "column_description": field.description,
                        "column_type": column_type,
                    }
                )
        return columns

    def get_table_lineage(
        self,
        urn,
        counts=100,
        direction="DOWNSTREAM",
        degree_values=None,
    ):
        # URN에 대한 DOWNSTREAM/UPSTREAM lineage entity를 counts 만큼 가져오는 함수
        # degree_values에 따라 lineage depth가 결정
        """
        Fetches downstream/upstream lineage entities for a given dataset URN using DataHub's GraphQL API.

        Args:
            urn (str): Dataset URN to fetch lineage for.
            count (int): Maximum number of entities to fetch (default=100).
            direction (str): DOWNSTREAM or UPSTREAM.
            degree_values (List[str]): Degree filter values like ["1", "2", "3+"]. Defaults to ["1", "2"].

        Returns:
            List[str, dict]: A list containing the dataset URN and its lineage result.
        """

        if degree_values is None:
            degree_values = ["1", "2"]

        graph = DataHubGraph(DatahubClientConfig(server=self.gms_server))

        query = """
            query scrollAcrossLineage($input: ScrollAcrossLineageInput!) {
            scrollAcrossLineage(input: $input) {
                searchResults {
                    degree
                    entity {
                        urn
                        type
                    }
                }
            }
        }
        """
        variables = {
            "input": {
                "query": "*",
                "urn": urn,
                "count": counts,
                "direction": direction,
                "orFilters": [
                    {
                        "and": [
                            {
                                "condition": "EQUAL",
                                "negated": "false",
                                "field": "degree",
                                "values": degree_values,
                            }
                        ]
                    }
                ],
            }
        }

        result = graph.execute_graphql(query=query, variables=variables)
        return urn, result

    def get_column_lineage(self, urn):
        # URN에 대한 UPSTREAM lineage의 column source를 가져오는 함수
        """
        Fetches fine-grained column-level lineage grouped by upstream datasets.

        Args:
            urn (str): Dataset URN to fetch lineage for.

        Returns:
            dict: {
                'downstream_dataset': str,
                'lineage_by_upstream_dataset': List[{
                    'upstream_dataset': str,
                    'columns': List[{'upstream_column': str, 'downstream_column': str}]
                }]
            }
        """

        # DataHub 연결 및 lineage 가져오기
        graph = DataHubGraph(DatahubClientConfig(server=self.gms_server))
        result = graph.get_aspect(entity_urn=urn, aspect_type=UpstreamLineageClass)

        # downstream dataset (URN 테이블명) 파싱
        try:
            down_dataset = urn.split(",")[1]
            table_name = down_dataset.split(".")[1]

        except IndexError:
            # URN이 유효하지 않는 경우
            print(f"[ERROR] Invalid URN format: {urn}")
            return {}

        # upstream_dataset별로 column lineage
        upstream_map = defaultdict(list)

        if not result:
            return {"downstream_dataset": table_name, "lineage_by_upstream_dataset": []}

        for fg in result.fineGrainedLineages or []:
            confidence_score = (
                fg.confidenceScore if fg.confidenceScore is not None else 1.0
            )
            for down in fg.downstreams:
                down_column = down.split(",")[-1].replace(")", "")
                for up in fg.upstreams:
                    up_dataset = up.split(",")[1]
                    up_dataset = up_dataset.split(".")[1]
                    up_column = up.split(",")[-1].replace(")", "")

                    upstream_map[up_dataset].append(
                        {
                            "upstream_column": up_column,
                            "downstream_column": down_column,
                            "confidence": confidence_score,
                        }
                    )

        # 최종 결과 구조 생성
        parsed_lineage = {
            "downstream_dataset": table_name,
            "lineage_by_upstream_dataset": [],
        }

        for up_dataset, column_mappings in upstream_map.items():
            parsed_lineage["lineage_by_upstream_dataset"].append(
                {"upstream_dataset": up_dataset, "columns": column_mappings}
            )

        return parsed_lineage

    def min_degree_lineage(self, lineage_result):
        # lineage 중 최소 degree만 가져오는 함수
        """
        Returns the minimum degree from the lineage result (fetched by get_table_lineage().)

        Args:
            lineage_result : (List[str, dict]): Result from get_table_lineage().

        Returns:
            dict : {table_name : minimum_degree}
        """

        table_degrees = {}

        urn, lineage_data = lineage_result

        for item in lineage_data["scrollAcrossLineage"]["searchResults"]:
            table = item["entity"]["urn"].split(",")[1]
            table_name = table.split(".")[1]
            degree = item["degree"]
            table_degrees[table_name] = min(
                degree, table_degrees.get(table_name, float("inf"))
            )

        return table_degrees

    def build_table_metadata(self, urn, max_degree=2, sort_by_degree=True):
        # 테이블 단위로 테이블 이름, 설명, 컬럼, 테이블 별 리니지(downstream/upstream), 컬럼 별 리니지(upstream)이 포함된 메타데이터 생성 함수
        """
        Builds table metadata including description, columns, and lineage info.

        Args:
            urn (str): Dataset URN
            max_degree (int): Max lineage depth to include (filtering)
            sort_by_degree (bool): Whether to sort downstream/upstream tables by degree

        Returns:
            dict: Table metadata
        """
        metadata = {
            "table_name": self.get_table_name(urn),
            "description": self.get_table_description(urn),
            "columns": self.get_column_names_and_descriptions(urn),
            "lineage": {},
        }

        def process_lineage(direction):
            # direction : DOWNSTREAM/UPSTREAM 별로 degree가 최소인 lineage를 가져오는 함수

            # 테이블 lineage 가져오기
            lineage_result = self.get_table_lineage(urn, direction=direction)
            table_degrees = self.min_degree_lineage(lineage_result)
            current_table_name = metadata["table_name"]

            # degree 필터링
            filtered_lineage = [
                {"table": table, "degree": degree}
                for table, degree in table_degrees.items()
                if degree <= max_degree and table != current_table_name
            ]

            # degree 기준 정렬
            if sort_by_degree:
                filtered_lineage.sort(key=lambda x: x["degree"])

            return filtered_lineage

        # DOWNSTREAM / UPSTREAM 링크 추가
        metadata["lineage"]["downstream"] = process_lineage("DOWNSTREAM")
        metadata["lineage"]["upstream"] = process_lineage("UPSTREAM")

        # 컬럼 단위 lineage 추가
        column_lineage = self.get_column_lineage(urn)
        metadata["lineage"]["upstream_columns"] = column_lineage.get(
            "lineage_by_upstream_dataset", []
        )

        return metadata

    def get_root_glossary_nodes(self):
        """
        DataHub에서 루트 용어집 노드를 가져오는 함수

        Returns:
            dict: 루트 용어집 노드 정보
        """
        # GraphQL 요청 보내기
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{self.gms_server}/api/graphql",
            json={"query": ROOT_GLOSSARY_NODES_QUERY},
            headers=headers,
        )

        # 결과 반환
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text,
            }

    def get_glossary_node_by_urn(self, urn):
        """
        DataHub에서 특정 URN의 용어집 노드 및 그 자식 항목을 가져오는 함수

        Args:
            urn (str): 용어집 노드의 URN

        Returns:
            dict: 용어집 노드 정보와 자식 항목
        """
        # GraphQL 요청 보내기
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{self.gms_server}/api/graphql",
            json={"query": GLOSSARY_NODE_QUERY, "variables": {"urn": urn}},
            headers=headers,
        )

        # 결과 반환
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text,
            }

    def get_node_basic_info(self, node, index):
        """
        용어집 노드의 기본 정보를 딕셔너리로 반환하는 함수

        Args:
            node (dict): 용어집 노드 정보
            index (int): 노드의 인덱스

        Returns:
            dict: 노드의 기본 정보
        """
        result = {"index": index, "name": node["properties"]["name"]}

        if node["properties"] and node["properties"].get("description"):
            result["description"] = node["properties"]["description"]

        # 자식 노드/용어 관계 정보 수 추가
        if "children" in node and node["children"]["total"] > 0:
            result["child_count"] = node["children"]["total"]

        return result

    def get_child_entity_info(self, entity, index):
        """
        자식 엔티티(용어 또는 노드)의 정보를 딕셔너리로 반환하는 함수

        Args:
            entity (dict): 자식 엔티티 정보
            index (int): 엔티티의 인덱스

        Returns:
            dict: 엔티티 정보
        """
        entity_type = entity["type"]
        result = {"index": index, "type": entity_type}

        if entity_type == "GLOSSARY_TERM":
            if "properties" in entity and entity["properties"]:
                result["name"] = entity["properties"].get("name", "N/A")

                if (
                    "description" in entity["properties"]
                    and entity["properties"]["description"]
                ):
                    result["description"] = entity["properties"]["description"]

        elif entity_type == "GLOSSARY_NODE":
            if "properties" in entity and entity["properties"]:
                result["name"] = entity["properties"].get("name", "N/A")

        return result

    def process_node_details(self, node):
        """
        노드의 상세 정보를 처리하고 딕셔너리로 반환하는 함수

        Args:
            node (dict): 용어집 노드 정보

        Returns:
            dict: 노드의 상세 정보
        """
        node_urn = node["urn"]
        detailed_node = self.get_glossary_node_by_urn(node_urn)

        result = {"name": node["properties"]["name"], "children": []}

        if (
            detailed_node
            and "data" in detailed_node
            and "glossaryNode" in detailed_node["data"]
        ):
            node_detail = detailed_node["data"]["glossaryNode"]

            # 자식 항목 정보 추출
            if "children" in node_detail and node_detail["children"]["total"] > 0:
                relationships = node_detail["children"]["relationships"]

                for j, rel in enumerate(relationships, 1):
                    entity = rel["entity"]
                    result["children"].append(self.get_child_entity_info(entity, j))

        return result

    def process_glossary_nodes(self, result):
        """
        용어집 노드 결과를 처리하고 딕셔너리로 반환하는 함수

        Args:
            result (dict): API 응답 결과

        Returns:
            dict: 처리된 용어집 노드 데이터
        """
        if "error" in result:
            return result

        processed_result = {"total_nodes": 0, "nodes": []}

        # 노드 목록 추출
        nodes = result["data"]["getRootGlossaryNodes"]["nodes"]
        processed_result["total_nodes"] = len(nodes)

        for i, node in enumerate(nodes, 1):
            node_info = self.get_node_basic_info(node, i)

            # 자식 노드가 있으면 상세 정보 처리
            if "children" in node and node["children"]["total"] > 0:
                node_details = self.process_node_details(node)
                node_info["details"] = node_details

            processed_result["nodes"].append(node_info)

        return processed_result

    def get_glossary_data(self):
        """
        DataHub에서 전체 용어집 데이터를 가져와 처리하는 함수

        Returns:
            dict: 처리된 용어집 데이터
        """
        # DataHub 서버에 연결하여 용어집 노드 가져오기
        result = self.get_root_glossary_nodes()

        # 결과 처리
        if result:
            try:
                return self.process_glossary_nodes(result)
            except KeyError as e:
                return {"error": True, "message": f"결과 구조 파싱 중 오류 발생: {e}"}
        else:
            return {"error": True, "message": "용어집 노드를 가져오지 못했습니다."}

    def get_queries(self, start=0, count=10, query="*", filters=None):
        """
        DataHub에서 쿼리 목록을 가져오는 함수

        Args:
            start (int): 시작 인덱스 (기본값=0)
            count (int): 반환할 쿼리 수 (기본값=10)
            query (str): 필터링에 사용할 쿼리 문자열 (기본값="*")
            filters (list): 추가 필터 (기본값=None)

        Returns:
            dict: 쿼리 목록 정보
        """
        # GraphQL 요청용 입력 변수 준비
        input_params = {"start": start, "count": count, "query": query}

        if filters:
            input_params["filters"] = filters

        variables = {"input": input_params}

        # GraphQL 요청 보내기
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{self.gms_server}/api/graphql",
            json={"query": LIST_QUERIES_QUERY, "variables": variables},
            headers=headers,
        )

        # 결과 반환
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text,
            }

    def process_queries(self, result):
        """
        쿼리 목록 결과를 처리하고 간소화된 형태로 반환하는 함수

        Args:
            result (dict): API 응답 결과

        Returns:
            dict: 처리된 쿼리 목록 데이터 (urn, name, description, statement만 포함)
        """
        if "error" in result:
            return result

        processed_result = {"total_queries": 0, "count": 0, "start": 0, "queries": []}

        if "data" in result and "listQueries" in result["data"]:
            list_queries = result["data"]["listQueries"]
            processed_result["total_queries"] = list_queries.get("total", 0)
            processed_result["count"] = list_queries.get("count", 0)
            processed_result["start"] = list_queries.get("start", 0)

            for query in list_queries.get("queries", []):
                query_info = {"urn": query.get("urn")}

                props = query.get("properties", {})
                query_info["name"] = props.get("name")
                query_info["description"] = props.get("description")
                query_info["statement"] = props.get("statement", {}).get("value")

                processed_result["queries"].append(query_info)

        return processed_result

    def get_query_data(self, start=0, count=10, query="*", filters=None):
        """
        DataHub에서 쿼리 목록을 가져와 처리하는 함수

        Args:
            start (int): 시작 인덱스 (기본값=0)
            count (int): 반환할 쿼리 수 (기본값=10)
            query (str): 필터링에 사용할 쿼리 문자열 (기본값="*")
            filters (list): 추가 필터 (기본값=None)

        Returns:
            dict: 처리된 쿼리 목록 데이터
        """
        # DataHub 서버에 연결하여 쿼리 목록 가져오기
        result = self.get_queries(start, count, query, filters)

        # 결과 처리
        if result:
            try:
                return self.process_queries(result)
            except KeyError as e:
                return {"error": True, "message": f"결과 구조 파싱 중 오류 발생: {e}"}
        else:
            return {"error": True, "message": "쿼리 목록을 가져오지 못했습니다."}

    def get_urn_info(self, urn):
        """
        특정 URN에 대한 모든 관련 정보를 가져오는 함수

        Args:
            urn (str): 조회할 데이터셋 URN

        Returns:
            dict: URN에 대한 전체 메타데이터 정보
        """
        print(f"\n=== URN 정보 조회: {urn} ===\n")

        try:
            # 기본 테이블 메타데이터 가져오기
            metadata = self.build_table_metadata(urn)

            # 결과 출력
            self._print_urn_details(metadata)

            return metadata

        except Exception as e:
            error_msg = f"URN 정보 조회 중 오류 발생: {str(e)}"
            print(error_msg)
            return {"error": True, "message": error_msg}

    def _print_urn_details(self, metadata):
        """URN 메타데이터를 보기 좋게 출력하는 내부 함수"""

        # 테이블 기본 정보
        print("📋 테이블 정보:")
        print(f"  이름: {metadata.get('table_name', 'N/A')}")
        print(f"  설명: {metadata.get('description', 'N/A')}\n")

        # 컬럼 정보
        columns = metadata.get("columns", [])
        if columns:
            print(f"📊 컬럼 정보 ({len(columns)}개):")
            for i, col in enumerate(columns, 1):
                print(f"  {i}. {col['column_name']} ({col.get('column_type', 'N/A')})")
                if col.get("column_description"):
                    print(f"     → {col['column_description']}")
            print()

        # 리니지 정보
        lineage = metadata.get("lineage", {})

        # Downstream 테이블
        downstream = lineage.get("downstream", [])
        if downstream:
            print(f"⬇️ Downstream 테이블 ({len(downstream)}개):")
            for table in downstream:
                print(f"  - {table['table']} (degree: {table['degree']})")
            print()

        # Upstream 테이블
        upstream = lineage.get("upstream", [])
        if upstream:
            print(f"⬆️ Upstream 테이블 ({len(upstream)}개):")
            for table in upstream:
                print(f"  - {table['table']} (degree: {table['degree']})")
            print()

        # 컬럼 레벨 리니지
        upstream_columns = lineage.get("upstream_columns", [])
        if upstream_columns:
            print("🔗 컬럼 레벨 리니지:")
            for upstream_dataset in upstream_columns:
                dataset_name = upstream_dataset["upstream_dataset"]
                columns = upstream_dataset["columns"]
                print(f"  📋 {dataset_name}:")
                for col in columns:
                    confidence = col.get("confidence", 1.0)
                    print(
                        f"    {col['upstream_column']} → {col['downstream_column']} (신뢰도: {confidence})"
                    )
            print()

    def get_queries_by_urn(self, dataset_urn):
        """
        특정 데이터셋 URN과 연관된 쿼리들을 조회하는 함수

        전체 쿼리를 가져온 후 클라이언트 사이드에서 필터링하는 방식 사용

        Args:
            dataset_urn (str): 데이터셋 URN

        Returns:
            dict: 연관된 쿼리 목록
        """
        # 먼저 전체 쿼리 목록을 가져옴
        input_params = {"start": 0, "count": 1000, "query": "*"}  # 충분히 큰 수로 설정

        variables = {"input": input_params}

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{self.gms_server}/api/graphql",
            json={"query": QUERIES_BY_URN_QUERY, "variables": variables},
            headers=headers,
        )

        if response.status_code == 200:
            result = response.json()
            if "data" in result and "listQueries" in result["data"]:
                # 클라이언트 사이드에서 특정 URN과 연관된 쿼리만 필터링
                all_queries = result["data"]["listQueries"]["queries"]
                filtered_queries = []

                for query in all_queries:
                    subjects = query.get("subjects", [])
                    for subject in subjects:
                        if subject.get("dataset", {}).get("urn") == dataset_urn:
                            filtered_queries.append(query)
                            break

                # 필터링된 결과로 응답 구조 재구성
                result["data"]["listQueries"]["queries"] = filtered_queries
                result["data"]["listQueries"]["count"] = len(filtered_queries)

            return result
        else:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text,
            }

    def get_glossary_terms_by_urn(self, dataset_urn):
        """
        특정 데이터셋 URN의 glossary terms를 조회하는 함수

        Args:
            dataset_urn (str): 데이터셋 URN

        Returns:
            dict: glossary terms 정보
        """
        variables = {"urn": dataset_urn}

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{self.gms_server}/api/graphql",
            json={"query": GLOSSARY_TERMS_BY_URN_QUERY, "variables": variables},
            headers=headers,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text,
            }


if __name__ == "__main__":
    fetcher = DatahubMetadataFetcher()

    print(
        fetcher.get_queries_by_urn(
            "urn:li:dataset:(urn:li:dataPlatform:dbt,small_bank_1.small_bank_1.ACCOUNTS,PROD)"
        )
    )
    print(
        fetcher.get_glossary_terms_by_urn(
            "urn:li:dataset:(urn:li:dataPlatform:dbt,small_bank_1.small_bank_1.ACCOUNTS,PROD)"
        )
    )
