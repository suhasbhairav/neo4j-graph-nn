from graph2data import build_pytorch_geometric_data
from graph_dbs import graph
import torch
from py2neo import Node, Relationship


def _mock_node_featurizer(node):
    if node['flavour'] == 'chocolate':
        return torch.tensor([1, 0, node['id']])
    elif node['flavour'] == 'vanilla':
        return torch.tensor([0, 1, node['id']])


def _mock_edge_featurizer(relationship):
    if "BETTER_THAN" in relationship.types():
        return torch.tensor([1, 0, relationship['id']])
    if "WORSE_THAN" in relationship.types():
        return torch.tensor([0, 1, relationship['id']])


def test_build_pytorch_geometric_data():
    bt = Relationship.type("BETTER_THAN")
    wt = Relationship.type("WORSE_THAN")
    nodes = [Node("ICE_CREAM", flavour="chocolate", niceness=10, id=0),
             Node("ICE_CREAM", flavour="chocolate", niceness=5, id=1),
             Node("ICE_CREAM", flavour="vanilla", niceness=8, id=2),
             Node("ICE_CREAM", flavour="vanilla", niceness=9, id=3)]
    rels = [bt(nodes[0], nodes[1], id=0),
            wt(nodes[1], nodes[2], id=1),
            bt(nodes[2], nodes[3], id=2),
            wt(nodes[3], nodes[0], id=3)]
    for node in nodes:
        graph._graph.create(node)
    for rel in rels:
        graph._graph.create(rel)
    try:
        matches = graph.run("MATCH (n:ICE_CREAM)-[r]->(m) RETURN n, r, m")

        data = build_pytorch_geometric_data(matches=matches,
                                            target_key='niceness',
                                            node_featurizer=_mock_node_featurizer,
                                            edge_featrizer=_mock_edge_featurizer)
        idx_map = {}
        for idt in range(4):
            nz = torch.nonzero(torch.stack(data.x)[:, 2] == idt)
            assert len(nz) == 1
            assert nz.item() not in idx_map.values()
            idx_map[idt] = nz.item()
        first_edge = torch.nonzero(torch.stack(data.edge_attr)[:, 2] == 0).item()
        assert data.edge_index[0][first_edge] == idx_map[0]
        assert data.edge_index[1][first_edge] == idx_map[1]
        last_edge = torch.nonzero(torch.stack(data.edge_attr)[:, 2] == 3).item()
        assert data.edge_index[0][last_edge] == idx_map[3]
        assert data.edge_index[1][last_edge] == idx_map[0]
    finally:
        for node in nodes:
            graph._graph.delete(node)
        for rel in rels:
            graph._graph.delete(rel)
