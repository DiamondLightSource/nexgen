import json
import tempfile

import pytest

from nexgen.nxs_utils import Axis, TransformationType


@pytest.fixture
def i24_axes_list() -> list[Axis]:
    return [
        Axis("omega", ".", TransformationType.ROTATION, (0, 0, -1)),
        Axis("sam_z", "omega", TransformationType.TRANSLATION, (0, 0, 1)),
        Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0)),
        Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0)),
    ]


@pytest.fixture
def dummy_chipmap():
    block_list = [1, 4]
    yield block_list


@pytest.fixture
def dummy_chipmap_full():
    block_list = [1, 2, 3, 4]
    yield block_list


@pytest.fixture
def dummy_xml_file():
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <ExtendedCollectRequests>
            <fileinfo>
                <directory>/path/to/data</directory>
                <prefix>Filename</prefix>
            </fileinfo>
            <runNumber>1</runNumber>
            <oscillation_sequence>
                <start>-180.0</start>
                <range>2.0</range>
                <number_of_images>10</number_of_images>
                <exposure_time>0.2</exposure_time>
                <number_of_passes>1</number_of_passes>
            </oscillation_sequence>
            <sampleDetectorDistanceInMM>110.0</sampleDetectorDistanceInMM>
            <transmissionInPerCent>10.0</transmissionInPerCent>
            <kappa>0.0</kappa>
            <axisChoice>Omega</axisChoice>
            <twoTheta>10.0</twoTheta>
            <otherAxis>-90.0</otherAxis>
            <resolution>1</resolution>
        </ExtendedCollectRequests>
    """
    test_xml_file = tempfile.NamedTemporaryFile(suffix=".xml", delete=True)
    with open(test_xml_file.name, "w") as f:
        f.write(test_xml)
    yield test_xml_file


@pytest.fixture
def dummy_geometry_json():
    test_geometry = {
        "sample_omega": {
            "depends_on": ".",
            "ds_name": "omega",
            "vector": [-1, 0, 0],
            "location": "sample",
            "units": "deg",
            "type": "rotation",
        },
        "geometry": "mcstas",
        "sample_x": {
            "depends_on": "omega",
            "ds_name": "sam_x",
            "vector": [1, 0, 0],
            "location": "sample",
            "units": "mm",
            "type": "translation",
        },
        "phi": {
            "depends_on": "sam_x",
            "ds_name": "phi",
            "vector": [0, 0, -1],
            "location": "sample",
            "units": "deg",
            "type": "rotation",
        },
        "detector_z": {
            "depends_on": ".",
            "ds_name": "det_z",
            "vector": [0, 0, 1],
            "location": "detector",
            "units": "mm",
            "type": "translation",
        },
    }
    test_json_file = tempfile.NamedTemporaryFile(suffix=".json", delete=True)
    with open(test_json_file.name, "w") as f:
        json.dump(test_geometry, f, indent=4)
    yield test_json_file


@pytest.fixture
def dummy_detector_json():
    test_detector = {
        "eiger": {
            "pixel_size_units": "m",
            "description": "Eiger 2X",
            "sensor_material": "CdTe",
            "pixel_size": [7.5e-05, 7.5e-05],
            "size": [2162, 2068],
            "fast_dir": [0, 1, 0],
            "slow_dir": [-1, 0, 0],
        }
    }
    test_json_file = tempfile.NamedTemporaryFile(suffix=".json", delete=True)
    with open(test_json_file.name, "w") as f:
        json.dump(test_detector, f, indent=4)
    yield test_json_file
