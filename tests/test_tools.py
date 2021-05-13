import nexgen


def test_cif2nxs():
    assert nexgen.imgcif2mcstas([0, 0, 0]) == (0, 0, 0)
    assert nexgen.imgcif2mcstas([1, 0, 0]) == (-1, 0, 0)
    assert nexgen.imgcif2mcstas([0, 1, 0]) == (0, 1, 0)
    assert nexgen.imgcif2mcstas([0, 0, 1]) == (0, 0, -1)
