import client_bank_1c


def test_loader(file_kl_to_1c):
    load = client_bank_1c.ClientBank1CLoader(fill_collected_fields=True)
    statement = load(file_kl_to_1c)
    assert statement.documents[0]['Получатель'] == ''
