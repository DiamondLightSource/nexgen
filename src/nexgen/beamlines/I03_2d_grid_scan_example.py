"""
Define beamline parameters for I03, Eiger detector and give an example of writing a gridscan.
"""
from contextlib import contextmanager
import h5py
from scanspec.specs import Line
import numpy as np
import shutil

from pathlib import Path
import os

# from nexgen.nxs_write import calculate_scan_from_scanspec

from nexgen.nxs_write.NexusWriter import call_writers, ScanReader
from nexgen.nxs_write.NXclassWriters import write_NXentry

from nexgen.tools.VDS_tools import image_vds_writer


source = {
    "name": "Diamond Light Source",
    "short_name": "DLS",
    "type": "Synchrotron X-ray Source",
    "beamline_name": "I03",
}


# fmt: off
goniometer_axes = {
    "axes": ["omega", "sam_z", "sam_y", "sam_x", "chi", "phi"],
    "depends": [".", "omega", "sam_z", "sam_y", "sam_x", "chi"],
    "vectors": [
        -1, 0.0, 0.0,
        0.0, 0.0, 1.0,
        0.0, 1.0, 0.0,
        1.0, 0.0, 0.0,
        0.006, -0.0264, 0.9996
        -1, -0.0025, -0.0056,
    ],
    "types": [
        "rotation",
        "translation",
        "translation",
        "translation",
        "rotation",
        "rotation",
    ],
    "units": ["deg", "mm", "mm", "mm", "deg", "deg"],
    "offsets": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "starts": [150.0, 0.0, 186.5867, 420.9968, 0.0, 0.0],
    "ends": [150.0, 0.0, 366.5867, 1040.9968, 0.0, 0.0],
    "increments": [0.0, 0.0, 18, 20, 0.0, 0.0],
}
# fmt: on

eiger16M_params = {
    "mode": "images",
    "description": "Eiger 16M",
    "detector_type": "Pixel",
    "sensor_material": "Silicon",
    "sensor_thickness": "4.5E-4",
    "overload": 46051,
    "underload": -1,  # Not sure of this
    "pixel_size": ["0.075mm", "0.075mm"],
    "flatfield": "flatfield",
    "flatfield_applied": "_dectris/flatfield_correction_applied",
    "pixel_mask": "mask",
    "pixel_mask_applied": "_dectris/pixel_mask_applied",
    "image_size": [2068, 2162],  # (fast, slow)
    "axes": ["det_z"],
    "depends": ["."],
    "vectors": [0.0, 0.0, 1.0],
    "types": ["translation"],
    "units": ["mm"],
    "starts": [391.228416716],
    "ends": [391.228416716],
    "increments": [0.0],
    "bit_depth_readout": "_dectris/bit_depth_readout",
    "detector_readout_time": "_dectris/detector_readout_time",
    "threshold_energy": "_dectris/threshold_energy",
    "software_version": "_dectris/software_version",
    "serial_number": "_dectris/detector_number",
    "beam_center": [1062.4015611483892, 1105.631937699275],
    "exposure_time": 0.004,
}

dset_links = [
    [
        "pixel_mask",
        "pixel_mask_applied",
        "flatfield",
        "flatfield_applied",
        "threshold_energy",
        "bit_depth_readout",
        "detector_readout_time",
        "serial_number",
    ],
    ["software_version"],
]

# Initialize dictionaries
goniometer = goniometer_axes
detector = eiger16M_params
module = {
    "fast_axis": [-1.0, 0.0, 0.0],
    "slow_axis": [0.0, -1.0, 0.0],
    "module_offset": "1",
}
beam = {"wavelength": 0.976253543307, "flux": 9.475216962184312e11}
attenuator = {"transmission": 0.4997258186340332}

TEST_FILENAME = "protk_1_1{}"
TEST_IMAGE_DATA = TEST_FILENAME.format("_000001.h5")
TEST_METAFILE = TEST_FILENAME.format("_meta.h5")
TEST_EXPECTED_NEXUS_FILE = TEST_FILENAME.format(".nxs")


@contextmanager
def get_test_data(remove_after_run=False):
    test_data_folder = Path(
        "/dls/i03/data/2022/cm31105-1/xraycentring/TestProteinaseK/protk_1/"
    )
    this_folder = Path(os.path.dirname(os.path.realpath(__file__)))
    files = []
    files.append(
        shutil.copy(test_data_folder / TEST_IMAGE_DATA, this_folder / TEST_IMAGE_DATA)
    )
    files.append(
        shutil.copy(test_data_folder / TEST_METAFILE, this_folder / TEST_METAFILE)
    )
    files.append(
        shutil.copy(
            test_data_folder / TEST_EXPECTED_NEXUS_FILE,
            this_folder / TEST_FILENAME.format("_expected.nxs"),
        )
    )
    try:
        yield
    finally:
        if remove_after_run:
            [os.remove(f) for f in files]


def example_nexus_file():
    """
    Creates an example nexus file that should closely match the expected file
    """

    # Get timestamps in the correct format
    timestamps = (
        "2022-01-19T11:23:50Z",
        "2022-01-19T11:24:01Z",
    )

    osc_scan, trans_scan = ScanReader(goniometer, snaked=True)

    containing_foler = Path(os.path.dirname(os.path.realpath(__file__)))
    test_nexus_file = containing_foler / "protk_1_1_test.nxs"
    image_data = [containing_foler / TEST_IMAGE_DATA]
    metafile = containing_foler / TEST_METAFILE

    if test_nexus_file.exists():
        print("File exists")
        os.remove(test_nexus_file)

    with h5py.File(test_nexus_file, "x") as nxsfile:
        nxentry = write_NXentry(nxsfile)

        if timestamps[0]:
            nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))

        call_writers(
            nxsfile,
            image_data,
            "mcstas",
            ("images", 320),
            goniometer,
            detector,
            module,
            source,
            beam,
            attenuator,
            osc_scan,
            trans_scan,
            metafile=metafile,
            link_list=dset_links,
        )

        # Write VDS
        image_vds_writer(
            nxsfile, (320, detector["image_size"][1], detector["image_size"][0])
        )

        if timestamps[1]:
            nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))


with get_test_data(True):
    example_nexus_file()
