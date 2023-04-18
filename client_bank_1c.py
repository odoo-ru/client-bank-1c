import datetime
import decimal
import io
import re
from typing import NamedTuple, List


class ClientBank1CStatement(NamedTuple):
    info: dict
    accounts: List[dict]
    documents: List[dict]


class ClientBank1CLoader:
    LINE_REGEXP = re.compile(r'(?P<key>\w+)(?:=(?P<value>.*))?')
    MONEY_FIELDS = {
        'НачальныйОстаток',
        'КонечныйОстаток',
        'ВсегоПоступило',
        'ВсегоСписано',
        'Сумма',
    }
    NUMBER_FIELDS = {'СрокАкцепта'}

    def __init__(self, money_type=decimal.Decimal, result_class=ClientBank1CStatement,
                 fill_collected_fields=False):
        self.money_type = money_type
        self.result_class = result_class
        self.fill_collected_fields = fill_collected_fields

    def from_file(self, file_path, encoding='cp1251'):
        with open(file_path, 'rb', encoding=encoding) as stream:
            return self(stream)

    def __call__(self, stream):
        if isinstance(stream, str):
            stream = io.StringIO(stream)
        elif isinstance(stream, bytes):
            stream = io.BytesIO(stream)

        if isinstance(stream, io.BytesIO):
            stream = io.TextIOWrapper(stream, encoding='cp1251')

        signature = stream.readline()
        assert signature == '1CClientBankExchange\n'

        info = {
            'РасчСчет': [],
            'Документ': [],
        }
        documents = []
        accounts = []
        section = 'info'
        for line in stream:
            if not line.strip():
                continue

            key, value = self._parse_line(line)

            if key == 'СекцияРасчСчет':
                assert section == 'info'
                section = key
                section_values = {}

            elif key == 'СекцияДокумент':
                assert section in {'info', False}
                section = key
                section_values = {'ВидДокумента': value}

            elif key == 'КонецРасчСчет':
                assert section == 'СекцияРасчСчет'
                section = False
                accounts.append(section_values)

            elif key == 'КонецДокумента':
                assert section == 'СекцияДокумент'
                section = False
                documents.append(section_values)

            elif key == 'КонецФайла':
                assert section in {False, 'info'}
                section = 'end'

            else:
                if section == 'info':
                    if key in {'РасчСчет', 'Документ'}:
                        info[key].append(value)
                    else:
                        info[key] = value
                else:
                    section_values[key] = value

        info, accounts, documents = self._process_result(info, accounts, documents)
        return self.result_class(info, accounts, documents)

    def _parse_line(self, line):
        key, value = self.LINE_REGEXP.match(line).groups()
        if 'Дата' in key:
            value = datetime.datetime.strptime(value, '%d.%m.%Y').date()
        elif 'Время' in key:
            value = datetime.datetime.strptime(value, '%H:%M:%S').time()
        elif key in self.MONEY_FIELDS:
            value = self.money_type(value)
        elif key in self.NUMBER_FIELDS and value:
            value = int(value)
        return key, value

    def _process_result(self, info, accounts, documents):
        if self.fill_collected_fields:
            for document in documents:
                if 'Получатель' not in document:
                    self._fill_collected_field(document, 'Получатель')

                if 'Плательщик' not in document:
                    self._fill_collected_field(document, 'Плательщик')

        return info, accounts, documents

    @staticmethod
    def _fill_collected_field(document, field_name):
        def get(field_suffix):
            return document.get(field_name + field_suffix)

        field_value = f"ИНН {get('ИНН')}\n{get('1')}\n\nр/с{get('2')}"
        if get('3'):
            field_value += '\n\nв ' + get('3')

        if get('4'):
            field_value += '\n\n' + get('4')

        document[field_name] = field_value


load = ClientBank1CLoader()
