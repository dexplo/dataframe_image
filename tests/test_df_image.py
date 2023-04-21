import numpy as np
import pandas as pd
import pytest

import dataframe_image

df = pd.read_csv(
    "tests/notebooks/data/covid19.csv", parse_dates=["date"], index_col="date"
)

test_dpi_values = [50, 100, 200, 400]
converters = ["chrome", "selenium", "matplotlib"]



class TestImage:
    @pytest.mark.parametrize("dpi", test_dpi_values)
    @pytest.mark.parametrize("converter", converters)
    def test_df(self, converter, dpi):
        df.tail(10).dfi.export(
            f"tests/test_output/covid19_{converter}_dpi{dpi}.png",
            table_conversion=converter,
            dpi=dpi,
        )


    @pytest.mark.parametrize("dpi", test_dpi_values)
    @pytest.mark.parametrize("converter", converters)
    def test_styled(self, converter, dpi):
        df.style.background_gradient().export_png(
            f"tests/test_output/covid19_styled_{converter}_dpi{dpi}.png",
            table_conversion=converter,
            dpi=dpi,
        )

    @pytest.mark.parametrize("dpi", test_dpi_values)
    @pytest.mark.parametrize("converter", converters)
    def test_huge_df(self, converter, dpi):
        df = pd.DataFrame(np.random.randint(0, 100, size=(300, 20)))
        df.dfi.export(
            f"tests/test_output/huge_{converter}_dpi{dpi}.png",
            table_conversion=converter,
            dpi=dpi,
            max_rows=-1,
        )
