"""
IO tool to gather beamline and collection information from xml file.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


class ExtendedRequestIO:
    """Define an ExtendedRequest object which in GDA gathers all the information regarding beamline and collection into an xml file."""

    def __init__(self, xmlfile: Path | str):
        self.tree = ET.parse(xmlfile)
        self.root = self.tree.getroot()

    def getCollectionInfo(self) -> tuple[str, str, str]:
        directory = self.root.find(".//directory").text
        prefix = self.root.find(".//prefix").text
        run_number = self.root.find(".//runNumber").text
        return directory, prefix, run_number

    def getOscillationSequence(self) -> dict[str, float]:
        osc_seq_node = self.root.find(".//oscillation_sequence")
        osc_seq = {
            "start": float(osc_seq_node.find(".//start").text),
            "range": float(osc_seq_node.find(".//range").text),
            "number_of_images": float(osc_seq_node.find(".//number_of_images").text),
            "exposure_time": float(osc_seq_node.find(".//exposure_time").text),
            "number_of_passes": float(osc_seq_node.find(".//number_of_passes").text),
        }
        return osc_seq

    def getAxisChoice(self) -> str:
        ax = self.root.find(".//axisChoice").text
        return ax.lower()

    def getOtherAxis(self) -> float:
        val = float(self.root.find(".//otherAxis").text)
        return val

    def getKappa(self) -> float:
        return float(self.root.find(".//kappa").text)

    def getChi(self) -> float:
        return float(self.root.find(".//chi").text)

    def getTwoTheta(self) -> float:
        return float(self.root.find(".//twoTheta").text)

    def getSampleDetectorDistance(self) -> float:
        return float(self.root.find(".//sampleDetectorDistanceInMM").text)

    def getTransmission(self) -> float:
        return float(self.root.find(".//transmissionInPerCent").text)

    def getResolution(self) -> float:
        return float(self.root.find(".//resolution").text)


def read_scan_from_xml(ecr: ExtendedRequestIO):
    """
    Extract information about the scan contained in the xml file.

    Args:
        ecr (ExtendedRequestIO): XML tree parser.
        xmlfile (Path | str): Path to xml file.

    Returns:
        scan_axis (str): Name of the rotation scan axis
        pos (dict): Dictionary containing the (start,end,increment) values for each goniometer axis.
        num (int): Number of images written.
    """
    # Goniometer
    osc_seq = ecr.getOscillationSequence()
    # Find scan range
    if osc_seq["range"] == 0.0:
        scan_range = (osc_seq["start"], osc_seq["start"])
        num = osc_seq["number_of_images"]
    else:
        start = osc_seq["start"]
        num = osc_seq["number_of_images"]
        stop = start + num * osc_seq["range"]
        scan_range = (start, stop)
    # Determine scan axis
    if ecr.getAxisChoice() == "omega":
        scan_axis = "omega"
        omega_pos = (*scan_range, osc_seq["range"])  # 0.0)
        phi_pos = (*2 * (ecr.getOtherAxis(),), 0.0)
    else:
        scan_axis = "phi"
        phi_pos = (*scan_range, osc_seq["range"])  # 0.0)
        omega_pos = (*2 * (ecr.getOtherAxis(),), 0.0)
    kappa_pos = (*2 * (ecr.getKappa(),), 0.0)

    pos = {
        "omega": omega_pos,
        "phi": phi_pos,
        "kappa": kappa_pos,
        "sam_x": (0.0, 0.0, 0.0),
        "sam_y": (0.0, 0.0, 0.0),
        "sam_z": (0.0, 0.0, 0.0),
    }

    return scan_axis, pos, int(num)


def read_det_position_from_xml(
    ecr: ExtendedRequestIO,
    det_description: str,
) -> list[float]:
    """Extract the detector position contained in the xml file.

    Args:
        ecr (ExtendedRequestIO): XML tree parser.
        det_description (str): Detector description

    Returns:
        list[float]: Detector axes positions in the order [2theta, det_z]
    """
    if "tristan" in det_description.lower():
        return [0.0, ecr.getSampleDetectorDistance()]
    elif "eiger" in det_description.lower():
        return [ecr.getTwoTheta(), ecr.getSampleDetectorDistance()]
    return [0.0, ecr.getSampleDetectorDistance()]
