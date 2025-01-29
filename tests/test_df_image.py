import random
import string
from io import BytesIO

import numpy as np
import pandas as pd
import pytest

import dataframe_image as dfi

df = pd.read_csv(
    "tests/notebooks/data/covid19.csv", parse_dates=["date"], index_col="date"
)

test_dpi_values = [100, 200, 300]
converters = ["chrome", "selenium", "matplotlib", "html2image", "playwright"]


@pytest.fixture
def get_df():
    return pd.read_csv(
        "tests/notebooks/data/covid19.csv", parse_dates=["date"], index_col="date"
    )


@pytest.mark.parametrize("dpi", test_dpi_values)
@pytest.mark.parametrize("converter", converters)
def test_df(document_name, converter, dpi):
    df.tail(10).dfi.export(
        f"tests/test_output/{document_name}.png",
        table_conversion=converter,
        dpi=dpi,
    )


@pytest.mark.parametrize("dpi", test_dpi_values)
@pytest.mark.parametrize("converter", converters)
def test_styled(document_name, converter, dpi):
    df.style.background_gradient().export_png(
        f"tests/test_output/{document_name}.png",
        table_conversion=converter,
        dpi=dpi,
    )


@pytest.mark.parametrize("converter", converters)
def test_styled2(document_name, converter):
    col_headers = {
        "selector": ".col_heading, thead",
        "props": "color: white; background-color: #1d5632; font-size: 11px",
    }

    df = pd.DataFrame(np.random.rand(6, 4))
    df_styled = df.style.set_table_styles([col_headers]).set_caption(
        "This is a caption"
    )
    dfi.export(
        df_styled, f"tests/test_output/{document_name}.png", table_conversion=converter
    )


@pytest.mark.asyncio
async def test_styled2_async(document_name):
    col_headers = {
        "selector": ".col_heading, thead",
        "props": "color: white; background-color: #1d5632; font-size: 11px",
    }

    df = pd.DataFrame(np.random.rand(6, 4))
    df_styled = df.style.set_table_styles([col_headers]).set_caption(
        "This is a caption"
    )
    await dfi.export_async(
        df_styled,
        f"tests/test_output/{document_name}_playwright_async.png",
        table_conversion="playwright_async",
    )
    await dfi.export_async(
        df_styled,
        f"tests/test_output/{document_name}_matplotlib_async.png",
        table_conversion="matplotlib",
    )


@pytest.mark.parametrize("dpi", test_dpi_values)
@pytest.mark.parametrize("converter", converters)
def test_huge_df(document_name, converter, dpi):
    df = pd.DataFrame(np.random.randint(0, 100, size=(300, 20)))
    df.dfi.export(
        f"tests/test_output/{document_name}.png",
        table_conversion=converter,
        dpi=dpi,
        max_rows=-1,
    )


def test_svg(document_name):
    dstyle = df.style.background_gradient()
    dfi.export(
        dstyle, f"tests/test_output/{document_name}.svg", table_conversion="matplotlib"
    )


@pytest.mark.parametrize("converter", converters)
def test_latex(document_name, converter):
    df_latex = pd.DataFrame([r"$\int^0_1 3x^2 dx$"])
    dfi.export(
        df_latex,
        f"tests/test_output/{document_name}.png",
        table_conversion=converter,
        use_mathjax=True,
    )


@pytest.mark.parametrize("dpi", test_dpi_values)
@pytest.mark.parametrize("converter", converters)
def test_long_column_headers(document_name, converter, dpi):
    column_headers = [
        "".join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=80))
        for _ in range(5)
    ]

    df = pd.DataFrame(np.random.randint(0, 100, size=(5, 5)), columns=column_headers)

    df.dfi.export(
        f"tests/test_output/{document_name}.png",
        table_conversion=converter,
        dpi=dpi,
        max_rows=-1,
    )


def test_save_using_bytesio():
    buf = BytesIO()
    df.dfi.export(buf, table_conversion="matplotlib")


def test_caption_cut(get_df):
    df = get_df.copy()
    styles = {}
    for key in df.columns:
        styles[key] = [
            {
                "selector": "th",
                "props": [
                    ("text-align", "center"),
                    ("background-color", "#40466e"),
                    ("color", "white"),
                ],
            }
        ]

    df = df.style.set_properties(subset=df.columns, **{"text-align": "center"}).hide(
        axis="index"
    )
    df = df.set_table_styles(styles)
    df = df.set_caption(
        "<h2 style='font-size: 16px'>Filial Weight of Flow - ytd_telegram</h2>"
    )

    dfi.export(
        df, "tests/test_output/caption_cut.png", table_conversion="chrome", max_rows=-1
    )


@pytest.mark.parametrize("converter", converters)
def test_complex_styled_df(document_name, get_df, converter):
    df = get_df.copy()
    table_styles = [
        {
            "selector": "thead th",  # Style pour les en-têtes de colonnes
            "props": [
                ("background-color", "blue"),  # Fond bleu
                ("color", "white"),  # Texte en blanc
                ("font-weight", "bold"),  # Texte en gras
                ("text-align", "center"),  # Centrer le texte
            ],
        },
        {
            "selector": "td",  # Style général pour toutes les cellules
            "props": [("border-right", "0.8px solid black")],
        },
        {
            "selector": "td.col0",  # Largeur spécifique pour la première colonne
            "props": [("width", "200px")],
        },
        # Appliquer une largeur spécifique à toutes les colonnes de la 2ᵉ à la dernière
        {
            "selector": "td:nth-child(n+2)",  # `nth-child(n+2)` cible la 2ᵉ colonne et au-delà
            "props": [("width", "70px")],
        },
    ]

    perf_indice_stylised = (
        df.style.set_properties(
            **{"text-align": "center"}
        )  # Centrer le contenu des colonnes
        .set_table_styles(table_styles, overwrite=False)  # Appliquer les propriétés CSS
        .bar(
            align=0,
            vmin=0,
            vmax=5000,
            height=50,
            width=50,
        )
        .hide(axis=0)  # Masquer l'index
    )

    image_path = f"tests/test_output/{document_name}.png"
    dfi.export(
        perf_indice_stylised,
        image_path,
        table_conversion=converter,
    )
