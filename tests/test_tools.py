import numpy as np
import pytest

import nexgen


def test_cif2nxs():
    assert nexgen.imgcif2mcstas([0, 0, 0]) == (0, 0, 0)
    assert nexgen.imgcif2mcstas([1, 0, 0]) == (-1, 0, 0)
    assert nexgen.imgcif2mcstas([0, 1, 0]) == (0, 1, 0)
    assert nexgen.imgcif2mcstas([0, 0, 1]) == (0, 0, -1)


def test_coord2nxs():
    R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    assert nexgen.coord2mcstas([0, 0, 0], R) == (0, 0, 0)
    assert nexgen.coord2mcstas([1, 0, 0], R) == (1, 0, 0)
    assert nexgen.coord2mcstas([0, 1, 0], R) == (0, 0, 1)
    assert nexgen.coord2mcstas([0, 0, 1], R) == (0, -1, 0)


def test_split_arrays():
    assert nexgen.split_arrays(["phi"], [1, 0, 0]) == {"phi": (1, 0, 0)}
    two_axes = nexgen.split_arrays(["omega", "phi"], [1, 0, 0, 0, 1, 0])
    assert two_axes["omega"] == (1, 0, 0) and two_axes["phi"] == (0, 1, 0)
    assert (
        len(
            nexgen.split_arrays(
                ["omega", "phi", "chi"], [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
            )
        )
        == 3
    )


def test_split_arrays_fails_if_wrong_size_arrays():
    with pytest.raises(ValueError):
        nexgen.split_arrays(["omega", "phi"], [1, 0, 0, 1])
