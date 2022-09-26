import pandas as pd
import pytest

import dataframe_image

df = pd.read_csv(
    "tests/notebooks/data/covid19.csv", parse_dates=["date"], index_col="date"
)

test_dpi_values = [50, 400, 600, 800]

class TestImage:
    def test_df(self):
        df.tail(10).dfi.export("tests/test_output/covid19.png")

    @pytest.mark.parametrize('dpi', test_dpi_values)
    def test_chrome_changed_dpi(self, dpi):
        df.tail(10).dfi.export(f"tests/test_output/covid19_dpi_{dpi}.png", dpi=dpi)

    def test_styled(self):
        df.tail(10).style.background_gradient().export_png(
            "tests/test_output/covid19_styled.png"
        )

    @pytest.mark.parametrize('dpi', test_dpi_values)
    def test_styled_changed_dpi(self, dpi):
        df.tail(10).style.background_gradient().export_png(
            f"tests/test_output/covid19_styled_dpi_{dpi}.png", dpi=dpi
        )

    def test_mpl(self):
        df.tail(10).dfi.export(
            "tests/test_output/covid19_mpl.png", table_conversion="matplotlib"
        )

    @pytest.mark.parametrize('dpi', test_dpi_values)
    def test_mpl_changed_dpi(self, dpi):
        df.tail(10).dfi.export(
            f"tests/test_output/covid19_mpl_dpi_{dpi}.png",
            table_conversion="matplotlib", dpi=dpi)
