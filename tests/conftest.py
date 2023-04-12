import pathlib

import pytest


@pytest.fixture(scope='session')
def data_dir():
    return pathlib.Path(__file__).parent / 'data'
