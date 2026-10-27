from workflow.process import scrape_data as sc_data
from tests.data import TEST_DATA_DIR
import pandas as pd
import json
import azfr_fsspec_utils as fspath
from prefect.logging import disable_run_logger


def get_input_data():
    input_process_path = fspath.join(TEST_DATA_DIR, 'offers_to_pd_input.json')
    with open(input_process_path, encoding="utf-8") as f:
        sample_data = json.load(f)
    return sample_data


def get_expected_data():
    expected_path = fspath.join(TEST_DATA_DIR, 'offers_to_pd_expected.csv')
    # keep_default_na=False pour conserver les cellules vides comme ""
    expected = pd.read_csv(
        expected_path,
        sep=';',
        encoding='utf-8',
        header=0,
        keep_default_na=False
    )
    return expected


class TestProcessSrapData:

    def test_get_expected_data(self):
        sample_data = get_input_data()

        with disable_run_logger():
            result = sc_data.offres_to_dataframe(sample_data)

        # Remplacer NaN ou pd.NA par "" pour éviter l'ambiguïté
        result = result.fillna("")
        expected = get_expected_data().fillna("")

        # Convertir toutes les colonnes contenant des dicts en chaînes
        dict_columns = ['lieuTravail', 'entreprise']
        for col in dict_columns:
            if col in result.columns:
                result[col] = result[col].apply(lambda x: str(x) if isinstance(x, dict) else x)
            if col in expected.columns:
                expected[col] = expected[col].apply(lambda x: str(x) if isinstance(x, dict) else x)

        pd.testing.assert_frame_equal(
            expected,
            result.reset_index(drop=True)
        )
