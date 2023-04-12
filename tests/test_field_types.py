import datetime

import client_bank_1c


def test_field_types(data_dir):
    with open(data_dir / 'kl_to_1c.txt', encoding='cp1251') as statement_file:
        statement = client_bank_1c.load(statement_file)

    assert statement.info['ДатаСоздания'] == datetime.date(2023, 1, 31)
    assert statement.info['ВремяСоздания'] == datetime.time(21, 0, 0)

    assert len(statement.accounts) == 1
    assert statement.accounts[0]['НачальныйОстаток'] == 110978.00

    assert len(statement.documents) == 1
