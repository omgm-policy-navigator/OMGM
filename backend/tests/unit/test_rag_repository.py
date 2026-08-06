from __future__ import annotations

import asyncio

from app.modules.rag.repository import SqlAlchemyRagSearchRepository


class MappingResult:
    def mappings(self) -> tuple[dict[str, object], ...]:
        return ()


class RecordingSession:
    statement: str = ""
    parameters: dict[str, object] = {}

    async def execute(self, statement: object, parameters: dict[str, object]) -> MappingResult:
        self.statement = str(statement)
        self.parameters = parameters
        return MappingResult()


def test_repository_enforces_all_rag_metadata_filters() -> None:
    asyncio.run(_assert_repository_enforces_all_rag_metadata_filters())


async def _assert_repository_enforces_all_rag_metadata_filters() -> None:
    session = RecordingSession()
    repository = SqlAlchemyRagSearchRepository(session)  # type: ignore[arg-type]

    await repository.search(
        policy_id="policy_selected",
        embedding=(0.1, 0.2),
        model="qwen3-embedding:0.6b",
        top_k=5,
        minimum_similarity=0.55,
    )

    assert "dc.policy_id = :policy_id" in session.statement
    assert "dc.document_status = 'APPROVED'" in session.statement
    assert "dc.trust_level = 'OFFICIAL'" in session.statement
    assert "dc.policy_status = 'ACTIVE'" in session.statement
    assert "dce.model = :model" in session.statement
    assert session.parameters["policy_id"] == "policy_selected"
    assert session.parameters["top_k"] == 5
