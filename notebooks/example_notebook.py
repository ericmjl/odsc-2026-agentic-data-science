# /// script
# dependencies = [
#     "marimo",
#     "numpy==2.4.4",
#     "plotly==6.7.0",
#     "polars==1.40.1",
#     "pyprojroot==0.3.0",
# ]
# requires-python = ">=3.13"
# ///

import marimo

__generated_with = "0.23.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # IRED deep mutational scan

    Supporting-information tables **cs1c02786_si_003** (chiral selectivity) and **cs1c02786_si_002**
    (enzyme activity) from a mutagenesis / DMS experiment on **IRED**. Paths resolve via `pyprojroot.here()`
    to `data/ired-novartis/`.

    Next steps: join or compare variants on `mutation`, explore distributions, etc.
    """)
    return


@app.cell
def _():
    return


@app.cell(hide_code=True)
def _():
    import polars as pl
    from pyprojroot import here

    _data_dir = here() / "data" / "ired-novartis"
    df_chiral_selectivity = pl.read_csv(_data_dir / "cs1c02786_si_003.csv")
    df_enzyme_activity = pl.read_csv(_data_dir / "cs1c02786_si_002.csv")
    return df_chiral_selectivity, df_enzyme_activity, pl


@app.cell
def _(df_chiral_selectivity):
    df_chiral_selectivity
    return


@app.cell
def _(df_enzyme_activity):
    df_enzyme_activity
    return


@app.cell
def _(mo):
    mo.md("""
    ### Activity vs chiral selectivity

    Reminder: both tables load from **`data/ired-novartis/`** via `here()` — enzyme activity (**si_002**) and chiral selectivity (**si_003**).

    Below we **inner-join on `mutation`** so each point is a variant measured in **both** assays:

    - **Horizontal axis (`mean`):** reported enzyme activity from the activity screen.
    - **Vertical axis (`r_enantiomeric_excess`):** enantiomeric excess from the selectivity assay.

    Use this scatter to see whether higher activity aligns with higher stereoselectivity for mutations observed in both datasets.
    """)
    return


@app.cell
def _(df_chiral_selectivity, df_enzyme_activity, mo):
    import plotly.graph_objects as pg_scatter

    joined = df_enzyme_activity.join(
        df_chiral_selectivity.select(["mutation", "r_enantiomeric_excess"]),
        on="mutation",
        how="inner",
    )

    _scatter_fig = pg_scatter.Figure(
        data=[
            pg_scatter.Scatter(
                x=joined["mean"].to_numpy(),
                y=joined["r_enantiomeric_excess"].to_numpy(),
                mode="markers",
                marker=dict(size=10, opacity=0.45, color="#2563eb"),
            )
        ]
    )
    _scatter_fig.update_layout(
        title=dict(text="Enzyme activity vs chiral selectivity (joined on mutation)"),
        xaxis_title="Enzyme activity (mean)",
        yaxis_title="Chiral selectivity (r enantiomeric excess)",
        template="plotly_white",
        height=520,
        margin=dict(l=60, r=20, t=50, b=50),
    )
    mo.ui.plotly(_scatter_fig)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Interpretation

    The scatter looks **weakly aligned at best** — activity (`mean`) and enantiomeric excess don’t march together in an obvious diagonal. That feels **reasonable**: turnover and stereochemical outcome can be **partially orthogonal** phenotypes under mutation. Improvements in catalytic flux don’t have to tighten selectivity (and vice versa); active-site changes can tune binding or hydride transfer without fixing the stereochemical manifold in the same way.

    Takeaway: treat **activity** and **selectivity** as related but distinct readouts unless the biology forces them to co-vary.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Position × mutant heatmaps (single substitutions)

    Below we keep only **single-point mutations** (`mutation` has **no** `;`), parse each label as **`WT{position}{mutant}`**, and tile **enzyme activity** (`mean`) and **chiral selectivity** (`r_enantiomeric_excess`) on the same grid: **x = sequence position**, **y = mutant (substituted) residue**. Where the same `(position, mutant)` appears more than once, we **average** the metric.

    Two **stacked Plotly** interactive heatmaps: **top** = activity, **bottom** = enantiomeric excess — shared positions and residue rows so you can compare patterns (pan/zoom/hover).
    """)
    return


@app.cell
def _(df_chiral_selectivity, df_enzyme_activity, mo, pl):
    import numpy as np
    import plotly.graph_objects as pg_hm
    from plotly.subplots import make_subplots

    _rx = r"^([A-Za-z])(\d+)([A-Za-z])$"

    def _single_mutants(df, value_col: str):
        """Single substitutions: `mutation` has no ';' and matches WT{pos}{mut}."""
        parsed = (
            df.filter(~pl.col("mutation").str.contains(";"))
            .with_columns(
                pl.col("mutation").str.extract(_rx, 2).cast(pl.Int64).alias("position"),
                pl.col("mutation")
                .str.extract(_rx, 3)
                .str.to_uppercase()
                .alias("mut_aa"),
            )
            .drop_nulls(["position", "mut_aa"])
        )
        return parsed.group_by(["position", "mut_aa"]).agg(pl.col(value_col).mean())

    def _build_grid(
        agg, value_col: str, positions: list[int], mutants: list[str]
    ) -> np.ndarray:
        lut = {
            (int(r["position"]), r["mut_aa"]): r[value_col]
            for r in agg.iter_rows(named=True)
        }
        z = np.full((len(mutants), len(positions)), np.nan)
        for i, aa in enumerate(mutants):
            for j, pos in enumerate(positions):
                z[i, j] = lut.get((pos, aa), np.nan)
        return z

    _act = _single_mutants(df_enzyme_activity, "mean")
    _ee = _single_mutants(df_chiral_selectivity, "r_enantiomeric_excess")

    _positions = sorted(
        set(_act["position"].to_list()) | set(_ee["position"].to_list())
    )
    _mutants = sorted(set(_act["mut_aa"].to_list()) | set(_ee["mut_aa"].to_list()))

    _z_act = _build_grid(_act, "mean", _positions, _mutants)
    _z_ee = _build_grid(_ee, "r_enantiomeric_excess", _positions, _mutants)

    _row_h = max(6.0, min(14.0, 0.22 * len(_mutants)))
    _col_w = max(10.0, min(28.0, 0.14 * len(_positions)))

    _hm_fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.09,
        subplot_titles=(
            "Single-point mutants — enzyme activity (mean)",
            "Single-point mutants — chiral selectivity (r enantiomeric excess)",
        ),
    )

    _hm_fig.add_trace(
        pg_hm.Heatmap(
            z=_z_act,
            x=_positions,
            y=_mutants,
            colorscale="Viridis",
            hovertemplate="position %{x}<br>mut %{y}<br>mean %{z}<extra></extra>",
            colorbar=dict(title=dict(text="mean"), len=0.45, y=0.78),
        ),
        row=1,
        col=1,
    )
    _hm_fig.add_trace(
        pg_hm.Heatmap(
            z=_z_ee,
            x=_positions,
            y=_mutants,
            colorscale="RdBu_r",
            hovertemplate="position %{x}<br>mut %{y}<br>EE %{z}<extra></extra>",
            colorbar=dict(title=dict(text="EE"), len=0.45, y=0.22),
        ),
        row=2,
        col=1,
    )

    _hm_fig.update_yaxes(autorange="reversed", row=1, col=1)
    _hm_fig.update_yaxes(autorange="reversed", row=2, col=1)

    _hm_fig.update_layout(
        template="plotly_white",
        height=int(max(580.0, _row_h * 72.0)),
        width=int(max(760.0, _col_w * 72.0)),
        margin=dict(l=72, r=120, t=70, b=56),
        showlegend=False,
    )
    _hm_fig.update_xaxes(title_text="Sequence position", row=2, col=1)
    _hm_fig.update_yaxes(title_text="Mutant residue", row=1, col=1)
    _hm_fig.update_yaxes(title_text="Mutant residue", row=2, col=1)

    mo.ui.plotly(_hm_fig)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Sampling note

    **Chiral-selectivity measurements in this dataset cluster in the regimes where enzyme activity was already relatively high.** That is mostly a sampling artifact: downstream stereochemistry assays are often run on subsets that look interesting from activity, so EE is not measured as evenly across the full activity landscape. Low-activity corners of the heatmap may be **under-sampled for EE**, not necessarily “no selectivity.”
    """)
    return


if __name__ == "__main__":
    app.run()
