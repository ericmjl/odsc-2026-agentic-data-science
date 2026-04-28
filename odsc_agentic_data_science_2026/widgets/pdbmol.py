"""Protein structure viewer built with `anywidget` and 3Dmol.js."""

from __future__ import annotations

from pathlib import Path

import anywidget
import traitlets as t

_HERE = Path(__file__).resolve().parent


class ProteinViewer3DMol(anywidget.AnyWidget):
    """Display a PDB structure in the browser using 3Dmol.js.

    The front-end loads 3Dmol from jsDelivr and fetches coordinates from RCSB
    via 3Dmol's ``pdb:<ID>`` loader. Valid PDB identifiers are four-character
    alphameric codes (older PDB convention).

    :ivar pdb_id: Four-letter PDB entry ID (case-insensitive), e.g. ``4HHB``.
    :ivar width: Viewer width in CSS pixels.
    :ivar height: Viewer height in CSS pixels.
    """

    _esm = _HERE / "pdbmol_viewer_esm.js"

    pdb_id = t.Unicode("4HHB").tag(sync=True)
    width = t.Int(720).tag(sync=True)
    height = t.Int(520).tag(sync=True)
