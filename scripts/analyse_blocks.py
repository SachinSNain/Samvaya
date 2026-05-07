"""Analyse blocking bucket size distribution to determine optimal MAX_BLOCK_SIZE."""
import sys, os
sys.path.insert(0, '.')
os.environ['SKIP_LLM_PARSING'] = 'true'

import pandas as pd, numpy as np
from collections import defaultdict
from src.normalisation.standardiser import standardise_record

records = []
for f, src in [
    ('data/raw/shop_establishment.csv', 'shop_establishment'),
    ('data/raw/factories.csv', 'factories'),
    ('data/raw/labour.csv', 'labour'),
    ('data/raw/kspcb.csv', 'kspcb'),
]:
    df = pd.read_csv(f).replace({np.nan: None}).to_dict('records')
    for r in df:
        r['source_system'] = src
        records.append(r)

normalised = [standardise_record(r, skip_geocoding=True) for r in records]

pin_soundex = defaultdict(list)
pin_meta    = defaultdict(list)
for rec in normalised:
    if rec.get('pin_code') and rec.get('soundex'):
        pin_soundex[f"{rec['pin_code']}_{rec['soundex']}"].append(rec['record_id'])
    if rec.get('pin_code') and rec.get('metaphone'):
        mk = rec['metaphone'][0] if isinstance(rec['metaphone'], tuple) else rec['metaphone']
        if mk:
            pin_meta[f"{rec['pin_code']}_{mk}"].append(rec['record_id'])

sizes_s = sorted([len(v) for v in pin_soundex.values()], reverse=True)
sizes_m = sorted([len(v) for v in pin_meta.values()],    reverse=True)

print('pin+soundex   top 15 bucket sizes:', sizes_s[:15])
print('pin+metaphone top 15 bucket sizes:', sizes_m[:15])

for cap in [200, 100, 50, 30, 20]:
    ps = sum(min(n, cap) * (min(n, cap) - 1) // 2 for n in sizes_s if n > 1)
    pm = sum(min(n, cap) * (min(n, cap) - 1) // 2 for n in sizes_m if n > 1)
    print(f'cap={cap:4d}  soundex_pairs={ps:>10,}  metaphone_pairs={pm:>10,}  total_key34={ps+pm:>10,}')
