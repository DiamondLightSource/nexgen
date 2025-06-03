import pytest

from nexgen.nxs_utils.sample import Sample


@pytest.fixture
def sample() -> Sample:
    return Sample(name="insulin", temperature=-10)


def test_sample(sample: Sample):
    assert sample.name == "insulin"
    assert not sample.depends_on


def test_sample_tpo_dict(sample: Sample):
    sample_dict = sample.to_dict()

    assert len(sample_dict.keys()) == 3
    assert sample_dict["name"] == "insulin"
    assert sample_dict["depends_on"] is None
    assert sample_dict["temperature"] == -10
