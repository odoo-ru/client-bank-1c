import pathlib

import pytest


@pytest.fixture(scope='session')
def data_dir():
    return pathlib.Path(__file__).parent / 'data'


@pytest.fixture()
def file_kl_to_1c(data_dir):
    with open(data_dir / 'kl_to_1c.txt', encoding='cp1251') as file:
        yield file
