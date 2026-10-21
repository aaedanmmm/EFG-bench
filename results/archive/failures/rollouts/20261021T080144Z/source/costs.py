"""Simulated order catalogue. All prices/units are constructed benchmark values."""
import copy
import json
from src.scenarios import ROOT

catalogue = json.loads((ROOT / "data" / "ordering_catalogue.json").read_text())


def get_catalogue():
    result = copy.deepcopy(catalogue)
    from src.fragments import get_fragments
    for name, metadata in get_fragments().items():
        result["items"][name] = {
            "category": "reagent", "description": f"Sequence-linked DNA aliquot: {name}",
            "price_cents": 15000, "unit": "50 uL aliquot", "volume_ul": 50,
            "component": name, "sequence": metadata,
            "concentration_ng_per_ul": 20.0,
            "physical_stock_provenance": "constructed benchmark assumption; not measured from FASTA",
        }
    from src.fragments import biochemistry_catalogue_items
    result["items"].update(biochemistry_catalogue_items())
    return result
