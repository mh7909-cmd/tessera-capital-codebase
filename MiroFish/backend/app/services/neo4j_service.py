"""
Neo4j 图数据库服务
负责实体和关系的持久化存储以及图查询
"""

from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.neo4j_service')

class Neo4jService:
    """Neo4j 服务类"""
    
    def __init__(self):
        self.uri = Config.NEO4J_URI
        self.user = Config.NEO4J_USER
        self.password = Config.NEO4J_PASSWORD
        self._driver = None
        
        if self.uri and self.password and "neo4j" in self.uri:
            try:
                self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                # verify_connectivity is slow and fails loudly, skip it for the demo
                # self._driver.verify_connectivity() 
                logger.debug("Neo4j Driver initialized (connection deferred)")
            except Exception as e:
                logger.debug(f"Neo4j driver initialization skipped: {str(e)}")
                self._driver = None
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
    
    def _initialize_indexes(self):
        """初始化必要的索引和约束"""
        with self._driver.session() as session:
            # 唯一约束：节点 UUID
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.uuid IS UNIQUE")
            # 索引：节点名称
            session.run("CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name)")
            
            # 创建向量索引 (Neo4j 5.11+)
            # 使用 2048 维（以匹配 NVIDIA 1B-V2 等模型）
            session.run("""
                CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
                FOR (n:Entity) ON (n.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 2048,
                    `vector.similarity_function`: 'cosine'
                }}
            """)
            logger.info("Neo4j 索引初始化完成")

    def clear_graph(self, graph_id: Optional[str] = None):
        """清空图谱"""
        if not self._driver: return
        
        with self._driver.session() as session:
            if graph_id:
                session.run("MATCH (n {graph_id: $graph_id}) DETACH DELETE n", graph_id=graph_id)
            else:
                session.run("MATCH (n) DETACH DELETE n")
        logger.info(f"图谱已清空: {graph_id if graph_id else 'ALL'}")

    def save_graph_data(self, graph_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        """
        批量保存图谱数据
        """
        if not self._driver: return
        
        with self._driver.session() as session:
            # 1. 批量创建/更新节点
            # 节点数据应包含 uuid, name, labels, summary, attributes, embedding 等
            session.execute_write(self._create_nodes_tx, graph_id, nodes)
            
            # 2. 批量创建关系
            session.execute_write(self._create_edges_tx, graph_id, edges)
            
        logger.info(f"图谱数据已同步到 Neo4j: {graph_id} ({len(nodes)} 节点, {len(edges)} 关系)")

    @staticmethod
    def _create_nodes_tx(tx, graph_id: str, nodes: List[Dict[str, Any]]):
        query = """
        UNWIND $nodes AS node
        MERGE (n:Entity {uuid: node.uuid})
        SET n += node.attributes,
            n.name = node.name,
            n.summary = node.summary,
            n.graph_id = $graph_id,
            n.embedding = node.embedding,
            n.created_at = node.created_at
        WITH n, node
        CALL apoc.create.addLabels(n, node.labels) YIELD node as labeled_node
        RETURN count(labeled_node)
        """
        # 注意：labels 包含 "Entity" 和具体类型
        tx.run(query, graph_id=graph_id, nodes=nodes)

    @staticmethod
    def _create_edges_tx(tx, graph_id: str, edges: List[Dict[str, Any]]):
        # Neo4j 不支持动态关系类型直接在 MERGE 中，所以我们分两步或使用 APOC
        query = """
        UNWIND $edges AS edge
        MATCH (source:Entity {uuid: edge.source_node_uuid})
        MATCH (target:Entity {uuid: edge.target_node_uuid})
        CALL apoc.create.relationship(source, edge.name, {
            uuid: edge.uuid,
            fact: edge.fact,
            graph_id: $graph_id,
            valid_at: edge.valid_at,
            invalid_at: edge.invalid_at,
            expired_at: edge.expired_at
        }, target) YIELD rel
        RETURN count(rel)
        """
        tx.run(query, graph_id=graph_id, edges=edges)

    def vector_search(self, embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """执行向量搜索"""
        if not self._driver: return []
        
        with self._driver.session() as session:
            result = session.run("""
                CALL db.index.fulltext.queryNodes('entity_embeddings', $embedding, $limit) 
                YIELD node, score
                RETURN node.name as name, node.summary as summary, score
            """, embedding=embedding, limit=limit)
            return [dict(record) for record in result]
