import pytest
from arrowport.models.arrow import ArrowBatch


def test_invalid_base64_data():
    batch = ArrowBatch(arrow_schema="invalid", data="invalid")
    with pytest.raises(ValueError):
        batch.to_arrow_table()
