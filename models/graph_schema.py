from dataclasses import dataclass
from typing import List, Dict

@dataclass
class GraphSchema:
    """Neo4j graph schema definition"""
    
    nodes: Dict[str, List[str]]
    relationships: List[str]
    indexes: List[str]
    constraints: List[str]

JOB_GRAPH_SCHEMA = GraphSchema(
    nodes={
        "Job": ["id", "title", "company", "location"],
        "Company": ["name"],
        "Skill": ["name"]
    },
    relationships=[
        "(:Company)-[:HAS_JOB]->(:Job)",
        "(:Job)-[:REQUIRES]->(:Skill)",
        "(:Company)-[:SIMILAR_TO]->(:Company)"
    ],
    indexes=[
        "CREATE INDEX job_id_index IF NOT EXISTS FOR (j:Job) ON (j.id)",
        "CREATE INDEX company_name_index IF NOT EXISTS FOR (c:Company) ON (c.name)",
        "CREATE INDEX skill_name_index IF NOT EXISTS FOR (s:Skill) ON (s.name)"
    ],
    constraints=[
        "CREATE CONSTRAINT job_id_unique IF NOT EXISTS FOR (j:Job) REQUIRE j.id IS UNIQUE"
    ]
)
