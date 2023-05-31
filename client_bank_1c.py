import datetime
import decimal
import io
import re
from typing import NamedTuple, List

DATE_FORMAT = '%d.%m.%Y'
TIME_FORMAT = '%H:%M:%S'
MONEY_FIELDS = {
    'НачальныйОстаток',
    'КонечныйОстаток',
    'ВсегоПоступило',
    'ВсегоСписано',
    'Сумма',
}


class ClientBank1CStatement(NamedTuple):
    info: dict
    accounts: List[dict]
    documents: List[dict]


class ClientBank1CLoader:
    LINE_REGEXP = re.compile(r'(?P<key>\w+)(?:=(?P<value>.*))?')
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
                assert section in {'info', False}
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
        if not value:
            return key, value

        if 'Дата' in key:
            value = datetime.datetime.strptime(value, DATE_FORMAT).date()
        elif 'Время' in key:
            value = datetime.datetime.strptime(value, TIME_FORMAT).time()
        elif key in MONEY_FIELDS:
            value = self.money_type(value)
        elif key in self.NUMBER_FIELDS:
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

        field_value = f"ИНН {get('ИНН')}\n{get('1')}"
        if get('2'):
            field_value += '\n\nр/с ' + get('2')

        if get('3'):
            field_value += '\n\nв ' + get('3')

        if get('4'):
            field_value += '\n\n' + get('4')

        document[field_name] = field_value


class ClientBank1CDump:
    INFO_DEFAULTS = {
        'ВерсияФормата': '1.03',
        'Кодировка': 'Windows',
        'Отправитель': 'Бухгалтерия предприятия, редакция 2.0',
    }

    EMPTY_VALUES = {False, None}

    def __call__(self, documents, info=None):
        result = '1CClientBankExchange\n'

        info = self._process_info(info or {})

        for key, value in info.items():
            result += self._render_line(key, value)

        for document in documents:
            result += self._render_line('РасчСчет', document['ПлательщикСчет'])

        for document in documents:
            result += self._render_line('СекцияДокумент', document['ВидДокумента'])
            for key, value in document.items():
                if key == 'ВидДокумента':
                    continue
                result += self._render_line(key, value)
            result += 'КонецДокумента\n'

        result += 'КонецФайла\n'

        coding = 'cp1251' if info['Кодировка'] == 'Windows' else 'cp866'
        return result.encode(coding)

    def _process_info(self, info):
        info = self._set_defaults(info)

        if 'ДатаСоздания' not in info:
            now = datetime.datetime.now()
            info['ДатаСоздания'] = now.today()
            info['ВремяСоздания'] = now.time()

        coding = info.get('Кодировка')
        if coding not in {'DOS', 'Windows'}:
            raise ValueError(f'Incorrect coding: {coding!r}')

        return info

    def _set_defaults(self, info):
        for key, value in self.INFO_DEFAULTS.items():
            info.setdefault(key, value)
        return info

    def _render_line(self, key, value):
        if value in self.EMPTY_VALUES:
            value = ''

        if not isinstance(value, str):
            if key in MONEY_FIELDS:
                value = format(value, '.2f')
            elif 'Дата' in key:
                value = format(value, DATE_FORMAT)
            elif 'Время' in key:
                value = format(value, TIME_FORMAT)
            else:
                value = str(value)

        return f'{key}={value}\n'


load = ClientBank1CLoader()
dump = ClientBank1CDump()
