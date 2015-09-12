import pytest
from app.el.misc import utils


@pytest.mark.parametrize('source,found', [
	('*found, gdhjk', ['found']),
	('**', []),
	('2*seven', ['seven'])
])
def test_mentions(source, found):
	assert set(utils.mentions(source)) == set(found)