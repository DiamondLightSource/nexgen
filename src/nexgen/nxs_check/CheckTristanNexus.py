"""
Tools to check and eventually fix NeXus files for Tristan LATRD detector on I19-2 beamline at DLS.
"""

import h5py
import logging

import numpy as np

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


def check_detector_transformations(NXtransf: h5py.Group):
    """
    Checks and eventually fixes the values of detector_z and two_theta fields and their attributes.
    """
    logger.info(
        "On I19-2 the Tristan detector does not sit on two_theta arm, which must be set to 0."
    )
    try:
        ds_name = "two_theta"
        two_theta = NXtransf["two_theta"]
    except KeyError:
        # For older versions of Tristan nexus file
        ds_name = "twotheta"
        two_theta = NXtransf["twotheta"]
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
    det_z = NXtransf["detector_z/det_z"]
    if det_z.attrs["vector"] != [0, 0, -1]:
        logger.info("Overwriting det_z vector ...")
        det_z.attrs["vector"] = [0, 0, -1]

    # TBD
    # logger.info("Checking dependency tree for typos ...")


def check_I19_dependency_tree(NXtransf: h5py.Group):
    """
    Check and fix that the dependency tree in "entry/sample/transformations" is consistent with I19-2.
    """
    # FIXME Quick hard coded way, works for now but needs to be generalized.
    logger.info("The dependency tree on I19-2 should follow this order:")
    logger.info("x - y - z - phi - kappa - omega")
    if NXtransf["omega"].attrs["depends_on"] != b".":
        NXtransf["omega"].attrs["depends_on"] = np.string_(".")
    if NXtransf["kappa"].attrs["depends_on"] != b"/entry/sample/transformations/omega":
        NXtransf["kappa"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/omega"
        )
    if NXtransf["phi"].attrs["depends_on"] != b"/entry/sample/transformations/kappa":
        NXtransf["phi"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/kappa"
        )
    if NXtransf["sam_x"].attrs["depends_on"] != b"/entry/sample/transformations/sam_y":
        NXtransf["sam_x"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/sam_y"
        )
    if NXtransf["sam_y"].attrs["depends_on"] != b"/entry/sample/transformations/sam_z":
        NXtransf["sam_y"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/sam_z"
        )
    if NXtransf["sam_z"].attrs["depends_on"] != b"/entry/sample/transformations/phi":
        NXtransf["sam_Z"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/phi"
        )


def run_checks(tristan_nexus_file):
    """
    Instigates the functions to check nexus files generated after binning of Tristan data.
    """
    wdir = tristan_nexus_file.parent
    logfile = wdir / "NeXusChecks.log"  # widr is a PosixPath
    logging.basicConfig(
        filename=logfile, format="%(asctime)s %(message)s", level="DEBUG", filemode="w"
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
        logger.info("Check goniometer dependency tree")
        check_I19_dependency_tree(nxsfile["entry/sample/transformations"])
        logger.info("EOF")
