"""
entity_resolution/ubid_assigner.py
Mints base-36 UBIDs and uses Union-Find to cluster auto-linked candidate pairs.
"""
import uuid
import string
from collections import defaultdict
from typing import List, Tuple

# "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE36_CHARS = string.digits + string.ascii_uppercase


def to_base36(num: int, length: int = 6) -> str:
    """Convert integer to base-36 string of fixed length."""
    result = []
    while num > 0:
        result.append(BASE36_CHARS[num % 36])
        num //= 36
    while len(result) < length:
        result.append('0')
    return ''.join(reversed(result))


def mint_ubid(existing: set = None) -> str:
    """Generate a new UBID: KA-UBID-XXXXXX, guaranteed unique against existing set."""
    for _ in range(100):
        uid = uuid.uuid4().int % (36 ** 6)
        candidate = f"KA-UBID-{to_base36(uid)}"
        if existing is None or candidate not in existing:
            return candidate
    raise RuntimeError("Failed to mint a unique UBID after 100 attempts")


class UnionFind:
    """Disjoint Set Union for entity clustering."""

    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        # Union by rank
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def get_clusters(self) -> dict:
        """Returns {cluster_root: [member_ids]}"""
        clusters = defaultdict(list)
        for node in self.parent:
            clusters[self.find(node)].append(node)
        return dict(clusters)


def assign_ubids(auto_link_pairs: List[Tuple[str, str]],
                 all_records: List[dict]) -> Tuple[dict, dict]:
    """
    Input:
        auto_link_pairs: list of (record_id_a, record_id_b) that scored >= AUTO_LINK threshold
        all_records: all normalised records with pan, gstin fields
    Returns:
        record_to_ubid: {record_id: ubid}
        ubid_to_anchor: {ubid: {"pan_anchor": str, "gstin_anchors": list, "anchor_status": str, "member_count": int}}
    """
    uf = UnionFind()

    # Add all records as individual nodes first (so even unlinked records get
    # a UBID)
    record_lookup = {r["record_id"]: r for r in all_records}
    for rec in all_records:
        uf.find(rec["record_id"])  # Initialises node

    # Union auto-linked pairs
    for rec_a_id, rec_b_id in auto_link_pairs:
        # Only union if both records actually exist in the records list
        if rec_a_id in record_lookup and rec_b_id in record_lookup:
            uf.union(rec_a_id, rec_b_id)

    # Get clusters
    clusters = uf.get_clusters()

    record_to_ubid = {}
    ubid_to_anchor = {}
    minted_ubids: set = set()

    for cluster_root, members in clusters.items():
        ubid = mint_ubid(minted_ubids)
        minted_ubids.add(ubid)

        # Determine PAN/GSTIN anchor for this cluster
        pan_anchor = None
        gstin_anchors = []
        for member_id in members:
            rec = record_lookup.get(member_id, {})
            pan = rec.get("pan")
            if pan and not pan_anchor:
                pan_anchor = pan

            gstin = rec.get("gstin")
            if gstin and gstin not in gstin_anchors:
                gstin_anchors.append(gstin)

        ubid_to_anchor[ubid] = {
            "pan_anchor": pan_anchor,
            "gstin_anchors": gstin_anchors,
            "anchor_status": "ANCHORED" if pan_anchor else "UNANCHORED",
            "member_count": len(members)
        }

        # Map each member to the new UBID
        for member_id in members:
            record_to_ubid[member_id] = ubid

    return record_to_ubid, ubid_to_anchor
