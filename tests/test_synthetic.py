from datetime import datetime

from pipeline.parse import parse_file
from pipeline.synthetic import header, sale_lines, trailer

DOWNLOADED = datetime(2026, 10, 19, 1, 0)


def make_sale(**overrides) -> dict:
    """A normal made-up sale; pass keyword arguments to change fields."""
    sale = {
        "property_id": "1000001", "sale_counter": "1", "downloaded": "20261019 01:00",
        "locality": "NORTHVALE", "post_code": "2999", "contract_date": "20260901",
        "settlement_date": "20261015", "price": "750000", "nature": "R",
        "dealing_number": "SY000001", "legal_description": "1/DP123456",
        "parties": ["P", "V"],
    }
    sale.update(overrides)
    return sale


def test_parse_reads_synthetic_file(tmp_path):
    long_legal = "LOT " * 30  # 120 characters -> split into 2 C records
    lines = [header("901", DOWNLOADED)]
    lines += sale_lines("901", make_sale(legal_description=long_legal))
    lines.append(trailer(lines))
    path = tmp_path / "901_SALES_DATA_NNME_19102026.DAT"
    path.write_text("\n".join(lines) + "\n")

    tables = parse_file(path)

    assert len(tables["B"]) == 1
    assert len(tables["C"]) == 2
    assert len(tables["D"]) == 2


import random
from datetime import date

from pipeline.synthetic import random_sale


def test_random_sale_is_repeatable():
    week = date(2026, 10, 19)
    first = random_sale(random.Random(42), week, counter=1, dealing=1)
    second = random_sale(random.Random(42), week, counter=1, dealing=1)
    assert first == second