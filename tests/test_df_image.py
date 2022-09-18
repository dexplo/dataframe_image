import pandas as pd
import pytest

import dataframe_image

df = pd.read_csv(
    "tests/notebooks/data/covid19.csv", parse_dates=["date"], index_col="date"
)


class TestImage:
    def test_df(self):
        df.tail(10).dfi.export("tests/test_output/covid19.png")

    def test_styled(self):
        df.tail(10).style.background_gradient().export_png(
            "tests/test_output/covid19_styled.png"
        )

    def test_styled_higher_device_scale_factor(self):
        df.tail(10).style.background_gradient().export_png(
            "tests/test_output/covid19_styled_dsf_4.png", device_scale_factor=4
        )

    def test_mpl(self):
        df.tail(10).dfi.export(
            "tests/test_output/covid19_mpl.png", table_conversion="matplotlib"
        )

    def test_mpl_higher_dpi(self):
        df.tail(10).dfi.export(
            "tests/test_output/covid19_mpl_dpi_600.png", table_conversion="matplotlib", savefig_dpi=600
        )