from conftest import cr

from changeguard.retrieval import cosine, mock_embed, retrieve_similar, rrf_fuse


def test_embed_deterministic():
    assert mock_embed("orders-db rebuild") == mock_embed("orders-db rebuild")
    assert cosine(mock_embed("a"), mock_embed("a")) == 1.0


def test_rrf_prefers_top_ranked():
    fused = dict(rrf_fuse([["a", "b", "c"], ["b", "a", "c"]]))
    assert fused["a"] > fused["c"] and fused["b"] > fused["c"]


def test_retrieve_returns_scored(history):
    res = retrieve_similar(cr(), history, top_k=3)
    assert len(res) == 3
    assert all(score > 0 for _, score in res)


def test_retrieve_linked_incidents(history):
    from changeguard.retrieval import linked_incidents
    incs = linked_incidents(cr(ci="payments-api"), history)
    assert "INC-1001" in incs
