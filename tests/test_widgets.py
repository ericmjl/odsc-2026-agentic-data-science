"""Tests for notebook widgets."""

from odsc_agentic_data_science_2026.widgets import ProteinViewer3DMol


def test_protein_viewer_traits_roundtrip() -> None:
    """Instantiate the 3Dmol-backed viewer and verify trait wiring."""
    w = ProteinViewer3DMol(pdb_id="1crn", width=400, height=300)
    assert w.pdb_id == "1crn"
    assert w.width == 400
    assert w.height == 300
    w.pdb_id = "4HHB"
    assert w.pdb_id == "4HHB"
