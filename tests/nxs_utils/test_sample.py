import pytest

from nexgen.nxs_utils.sample import Sample


@pytest.fixture
def sample() -> Sample:
    return Sample(name="insulin", temperature=-10)


def test_sample(sample: Sample):
    assert sample.name == "insulin"
    assert not sample.depends_on
    assert not sample.pressure
    assert sample.temperature == -10


def test_sample_info_dict(sample: Sample):
    sample_dict = sample.get_sample_info_as_dict()

    assert len(sample_dict.keys()) == 2
    assert sample_dict["name"] == "insulin"
    assert "depends_on" not in sample_dict.keys()
    assert sample_dict["temperature"] == -10


def test_sample_returns_no_dict_if_only_depends_on_is_set():
    only_dep_sample = Sample(depends_on="phi")

    assert not only_dep_sample.get_sample_info_as_dict()
