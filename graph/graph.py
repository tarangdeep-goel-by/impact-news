"""NetworkX DiGraph wrapper for the impact graph."""

from collections import deque
from pathlib import Path

import networkx as nx
import yaml

from models import Edge, Node


class ImpactGraph:
    def __init__(self, graph_path: str = "data/merged_graph.yaml"):
        self.graph_path = Path(graph_path)
        self.g = nx.DiGraph()

    def load(self) -> None:
        """Parse YAML and populate the NetworkX DiGraph."""
        with open(self.graph_path) as f:
            data = yaml.safe_load(f)

        for n in data.get("nodes", []):
            node = Node(**n)
            self.g.add_node(
                node.id,
                aliases=node.aliases,
                category=node.category,
                is_category=node.is_category,
            )

        for e in data.get("edges", []):
            self.g.add_edge(
                e["from"],
                e["to"],
                type=e.get("type", ""),
                description=e.get("description", ""),
                weight=e.get("weight", 1.0),
            )

    def get_node(self, node_id: str) -> Node | None:
        if node_id not in self.g:
            return None
        attrs = self.g.nodes[node_id]
        return Node(
            id=node_id,
            aliases=attrs.get("aliases", []),
            category=attrs.get("category", ""),
            is_category=attrs.get("is_category", False),
        )

    def get_neighbors(self, node_id: str, direction: str = "both") -> list[str]:
        if node_id not in self.g:
            return []
        if direction == "in":
            return self.get_predecessors(node_id)
        if direction == "out":
            return self.get_successors(node_id)
        return list(set(self.g.predecessors(node_id)) | set(self.g.successors(node_id)))

    def get_predecessors(self, node_id: str) -> list[str]:
        if node_id not in self.g:
            return []
        return list(self.g.predecessors(node_id))

    def get_successors(self, node_id: str) -> list[str]:
        if node_id not in self.g:
            return []
        return list(self.g.successors(node_id))

    def backward_bfs(self, start_nodes: list[str], max_hops: int = 3) -> set[str]:
        """BFS in reverse direction (predecessors) up to max_hops."""
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()

        for node in start_nodes:
            if node in self.g:
                visited.add(node)
                queue.append((node, 0))

        while queue:
            current, depth = queue.popleft()
            if depth >= max_hops:
                continue
            for pred in self.g.predecessors(current):
                if pred not in visited:
                    visited.add(pred)
                    queue.append((pred, depth + 1))

        return visited

    def find_path(self, source: str, target: str) -> list[Edge] | None:
        """Shortest path as a list of Edge objects, or None."""
        try:
            path = nx.shortest_path(self.g, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        edges = []
        for u, v in zip(path[:-1], path[1:]):
            attrs = self.g.edges[u, v]
            edges.append(
                Edge(
                    from_node=u,
                    to_node=v,
                    type=attrs.get("type", ""),
                    description=attrs.get("description", ""),
                    weight=attrs.get("weight", 1.0),
                )
            )
        return edges

    def get_all_aliases(self) -> list[tuple[str, str]]:
        """Return (node_id, alias) pairs. Includes node ID itself as an alias."""
        result = []
        for node_id, attrs in self.g.nodes(data=True):
            result.append((node_id, node_id))
            for alias in attrs.get("aliases", []):
                result.append((node_id, alias))
        return result

    def stats(self) -> dict:
        """Graph statistics."""
        degree_list = sorted(self.g.degree(), key=lambda x: x[1], reverse=True)
        total_degree = sum(d for _, d in degree_list)
        n = self.g.number_of_nodes()

        return {
            "node_count": n,
            "edge_count": self.g.number_of_edges(),
            "connected_components": nx.number_weakly_connected_components(self.g),
            "avg_degree": round(total_degree / n, 2) if n else 0,
            "top_10_by_degree": degree_list[:10],
        }
