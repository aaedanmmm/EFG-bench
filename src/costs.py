"""Simulated order catalogue. All prices/units are constructed benchmark values."""
import copy
import json
from src.scenarios import ROOT

catalogue = json.loads((ROOT / "data" / "ordering_catalogue.json").read_text())


def get_catalogue():
    return copy.deepcopy(catalogue)
