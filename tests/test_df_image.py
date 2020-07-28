import pytest
import pandas as pd
import dataframe_image


df = pd.read_csv('tests/notebooks/data/covid19.csv', parse_dates=['date'], index_col='date')


class TestImage:    

    def test_df(self):
        df.tail(10).dfi.export('tests/test_output/covid19.png')

    def test_styled(self):
        df.tail(10).style.background_gradient().export_png('tests/test_output/covid19_styled.png')

    def test_mpl(self):
        df.tail(10).dfi.export('tests/test_output/covid19_mpl.png', table_conversion='matplotlib')