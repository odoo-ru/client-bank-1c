import os
import io

import pytest

import client_bank_1c

BASE_DIR = os.path.dirname(__file__)
min_example_path = os.path.join(BASE_DIR, 'data/1c_to_kl-win-min-example.txt')
with open(min_example_path, encoding='cp1251') as min_example_file:
    min_example = min_example_file.read()


@pytest.mark.parametrize('data', [
    min_example,
    min_example.encode('cp1251'),
    io.StringIO(min_example),
    io.BytesIO(min_example.encode('cp1251')),
    open(min_example_path, encoding='cp1251'),
])
def test_input_data_types(data):
    statement = client_bank_1c.load(data)
    assert statement.info == {
        'РасчСчет': [],
        'Документ': [],
        'Поле': 'Значение',
    }
    assert not statement.accounts
    assert not statement.documents
