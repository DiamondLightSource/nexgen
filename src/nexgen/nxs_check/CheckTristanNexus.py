"""
Tools to check and eventually fix NeXus files for Tristan LATRD detector on I19-2 beamline at DLS.
"""

import sys
import h5py
import logging

import numpy as np

from pathlib import Path

# Define logger
logger = logging.getLogger("TristanNXSChecks")


def check_definition(nxsfile: h5py.File):
    """
    Checks and eventually fixes that the definition is set to "NXmx"
    """
    definition = nxsfile["entry/definition"][()]
    logger.info(f"Application definition: {definition}")
    if definition != "NXmx":
        del nxsfile["entry/definition"]
        nxsfile["entry"].create_dataset("definition", data="NXmx")
        logger.info("Fixing definition to NXmx")
    logger.info("")


def check_detector_transformations(nxtransf: h5py.Group):
    """
    Checks and eventually fixes the values of detector_z and two_theta fields and their attributes.
    """
    logger.info(
        "On I19-2 the Tristan detector does not sit on two_theta arm, which must be set to 0."
    )
    try:
        ds_name = "two_theta"
        two_theta = nxtransf["two_theta"]
    except KeyError:
        # For older versions of Tristan nexus file
        ds_name = "twotheta"
        two_theta = nxtransf["twotheta"]
    if two_theta[ds_name][()] != 0:
        logger.info("Correcting the value of two_theta arm ...")
        d = {}
        for k in two_theta[ds_name].attrs.keys():
            d[k] = two_theta[ds_name].attrs[k]
        del two_theta[ds_name]
        tt = two_theta.create_dataset(ds_name, data=[(0.0)])
        for k, v in d.items():
            tt.attrs[k] = v
        del d

    logger.info("Additionally, the detector_z vector should be [0,0,-1]")
    det_z = nxtransf["detector_z/det_z"]
    if np.any(det_z.attrs["vector"] != [0, 0, 1]):
        logger.info("Overwriting det_z vector ...")
        det_z.attrs["vector"] = [0, 0, 1]  # [0,0,-1]

    logger.info("Checking dependency tree of detector for typos ...")
    if two_theta[ds_name].attrs["depends_on"] != b".":
        logger.info("Setting two_theta as base ...")
        two_theta[ds_name].attrs["depends_on"] = np.string_(".")
    if (
        det_z.attrs["depends_on"]
        != b"/entry/instrument/detector/transformations/two_theta/two_theta"
    ):
        logger.info("Fixing typo in det_z dependency ...")
        det_z.attrs["depends_on"] = np.string_(
            "/entry/instrument/detector/transformations/two_theta/two_theta"
        )


def check_sample_depends_on(nxsample: h5py.Group):
    """
    Check that the sample depends_on field exists and is correct.
    For I19-2 Tristan it should be "/entry/sample/transformations/phi"
    """
    try:
        dep = nxsample["depends_on"][()]
        if dep != b"/entry/sample/transformations/phi":
            logger.info("Fixing sample depends_on field ...")
            del nxsample["depends_on"]
            nxsample.create_dataset(
                "depends_on", data=np.string_("/entry/sample/transformations/phi")
            )
    except KeyError:
        logger.info("Sample depends_on field did not exist, creating now ...")
        nxsample.create_dataset(
            "depends_on", data=np.string_("/entry/sample/transformations/phi")
        )


def check_I19_dependency_tree(nxtransf: h5py.Group):
    """
    Check and fix that the dependency tree in "entry/sample/transformations" is consistent with I19-2.
    """
    # FIXME Quick hard coded way, works for now but needs to be generalized.
    logger.info("The dependency tree on I19-2 should follow this order:")
    logger.info("x - y - z - phi - kappa - omega")
    if nxtransf["omega"].attrs["depends_on"] != b".":
        logger.info("Fixing omega ...")
        nxtransf["omega"].attrs["depends_on"] = np.string_(".")
    if nxtransf["kappa"].attrs["depends_on"] != b"/entry/sample/transformations/omega":
        logger.info("Fixing kappa ...")
        nxtransf["kappa"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/omega"
        )
    if nxtransf["phi"].attrs["depends_on"] != b"/entry/sample/transformations/kappa":
        logger.info("Fixing phi ...")
        nxtransf["phi"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/kappa"
        )
    if nxtransf["sam_x"].attrs["depends_on"] != b"/entry/sample/transformations/sam_y":
        logger.info("Fixing sam_x dependency...")
        nxtransf["sam_x"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/sam_y"
        )
    if np.any(nxtransf["sam_x"].attrs["vector"] != [-1, 0, 0]):
        logger.info("Fixing sam_x vector...")
        nxtransf["sam_x"].attrs["vector"] = [-1, 0, 0]
    if nxtransf["sam_y"].attrs["depends_on"] != b"/entry/sample/transformations/sam_z":
        logger.info("Fixing sam_y ...")
        nxtransf["sam_y"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/sam_z"
        )
    if np.any(nxtransf["sam_y"].attrs["vector"] != [0, -1, 0]):
        logger.info("Fixing sam_y vector...")
        nxtransf["sam_y"].attrs["vector"] = [0, -1, 0]
    if nxtransf["sam_z"].attrs["depends_on"] != b"/entry/sample/transformations/phi":
        logger.info("Fixing sam_z ...")
        nxtransf["sam_z"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/phi"
        )
    if np.any(nxtransf["sam_z"].attrs["vector"] != [0, 0, -1]):
        logger.info("Fixing sam_z vector...")
        nxtransf["sam_z"].attrs["vector"] = [0, 0, -1]


def check_values(nxentry: h5py.Group):
    """
    Checks tht all dataset values that are supposed to be floats/ints aren't saved as strings.
    """
    instr = nxentry["instrument"]
    if type(instr["beam/incident_wavelength"][()]) is bytes:
        logger.info("Fixing incident wavelength value ...")
        d = {}
        for k, v in instr["beam/incident_wavelength"].attrs.items():
            d[k] = v
        val = float(instr["beam/incident_wavelength"][()])
        del instr["beam/incident_wavelength"]
        wl = instr["beam"].create_dataset("incident_wavelength", data=val)
        for k, v in d.items():
            wl.attrs[k] = v
        del d, val
    if type(instr["attenuator/attenuator_transmission"][()]) is bytes:
        logger.info("Fixing attenuator transmission value...")
        val = float(instr["attenuator/attenuator_transmission"][()])
        del instr["attenuator/attenuator_traansmission"]
        instr["attenuator"].create_dataset("attenuator_transmission", data=val)
        del val
    det = nxentry["instrument/detector"]
    if type(det["sensor_thickness"][()]) is np.bytes_:
        logger.info("Fixing sensor thickness value ...")
        d = {}
        for k, v in det["sensor_thickness"].attrs.items():
            d[k] = v
        val = float(det["sensor_thickness"][()])
        del det["sensor_thickness"]
        th = det.create_dataset("sensor_thickness", data=val)
        for k, v in d.items():
            th.attrs[k] = v
        del d, val


def run_checks(tristan_nexus_file):
    """
    Instigates the functions to check nexus files generated after binning of Tristan data.
    """
    if type(tristan_nexus_file) is str:
        tristan_nexus_file = Path(tristan_nexus_file).expanduser().resolve()
    wdir = tristan_nexus_file.parent
    logfile = wdir / "NeXusChecks.log"  # widr is a PosixPath
    logging.basicConfig(
        filename=logfile, format="%(message)s", level="DEBUG", filemode="a"
    )
    logger.info(f"Running checks on {tristan_nexus_file} ...")

    with h5py.File(tristan_nexus_file, "r+") as nxsfile:
        logger.info("Check application definition")
        check_definition(nxsfile)
        logger.info("-" * 10)
        logger.info(
            "Check that detector_z and two_theta fields are correctly set to I19-2 configuration for Tristan."
        )
        try:
            # According to NXmx Gold Standard
            check_detector_transformations(
                nxsfile["entry/instrument/detector/transformations"]
            )
        except KeyError:
            # For earlier versions of the Tristan nexus file (before June 2021):
            # NXtransformations group was placed under NXinstrument group
            check_detector_transformations(nxsfile["entry/instrument/transformations"])
        logger.info("-" * 10)
        logger.info("Check sample depends on")
        check_sample_depends_on(nxsfile["entry/sample"])
        logger.info("-" * 10)
        logger.info("Check goniometer dependency tree")
        check_I19_dependency_tree(nxsfile["entry/sample/transformations"])
        logger.info("-" * 10)
        logger.info("Check that number values are saved as floats and not strings")
        check_values(nxsfile["entry"])
        logger.info("EOF")


run_checks(sys.argv[1])
