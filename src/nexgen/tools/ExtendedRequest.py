"""
IO tool to gather beamline and collection information from xml file.
"""

import xml.etree.ElementTree as ET

from pathlib import Path
from typing import Dict, Tuple, Union


class ExtendedRequestIO:
    def __init__(self, xmlfile: Union[Path, str]):
        self.tree = ET.parse(xmlfile)
        self.root = self.tree.getroot()

    def getCollectionInfo(self) -> Tuple[str, str, str]:
        directory = self.root.find(".//directory").text
        prefix = self.root.find(".//prefix").text
        run_number = self.root.find(".//runNumber").text
        return directory, prefix, run_number

    def getOscillationSequence(self) -> Dict[str, float]:
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
