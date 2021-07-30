"""
Tools to check and eventually fix NeXus files for Tristan LATRD detector.
"""

import h5py
import logging

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

    logger.info("Checking dependency tree for typos ...")


def run_checks(tristan_nexus_file):
    """
    Instigates the functions to check nexus files generated after binning of Tristan data.
    """
    wdir = tristan_nexus_file.parent
    logfile = wdir / "NeXusChecks.log"  # widr is a PosixPath
    logging.basicConfig(
        filename=logfile,
        format="%(message)s",
        level="DEBUG",
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
        logger.info("EOF")
