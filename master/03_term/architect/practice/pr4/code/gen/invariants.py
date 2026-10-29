# AUTO-GENERATED из model/pim.yaml (generator/generate.py). Не править вручную.
# Исполняемые версии OCL-инвариантов; используются тестами для сверки с БД.
import re  # noqa: F401
from decimal import Decimal  # noqa: F401

SCALAR = {}   # инвариант -> (сущность, функция-предикат над строкой)
UNIQUE = {}   # инвариант -> (сущность, поля ключа)

def inv5_value(value):
    # OCL: self.matches('[A-Z]{3}')
    return bool(re.fullmatch(r'[A-Z]{3}', value))

def inv5(row):
    return inv5_value(row.baseCurrency) and inv5_value(row.quoteCurrency)

SCALAR['INV-5'] = ('ExchangeRate', inv5)

UNIQUE['INV-1'] = ('IngestionBatch', ('source', 'batchKey'))  # OCL: IngestionBatch.allInstances()->isUnique(b | Tuple{s = b.source, k = b.batchKey})

def inv2(row):
    # OCL: self.rate > 0
    return row.rate > 0

SCALAR['INV-2'] = ('ExchangeRate', inv2)

def inv3(row):
    # OCL: self.baseCurrency <> self.quoteCurrency
    return row.baseCurrency != row.quoteCurrency

SCALAR['INV-3'] = ('ExchangeRate', inv3)

UNIQUE['INV-4'] = ('ExchangeRate', ('batch', 'baseCurrency', 'quoteCurrency', 'rateDate'))  # OCL: ExchangeRate.allInstances()->isUnique(r | Tuple{b = r.batch, c1 = r.baseCurrency, c2 = r.quoteCurrency, d = r.rateDate})
