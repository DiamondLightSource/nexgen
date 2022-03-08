"""
IO tool to gather beamline and collection information from xml file.
"""

import xml.etree.ElementTree as ET


class ExtendedRequestIO:
    def __init__(self, xmlfile):
        self.tree = ET.parse(xmlfile)
        self.root = self.tree.getroot()

    def getCollectionInfo(self):
        directory = self.root.find(".//directory").text
        prefix = self.root.find(".//prefix").text
        run_number = self.root.find(".//runNumber").text
        return directory, prefix, run_number

    def getOscillationSequence(self):
        osc_seq_node = self.root.find(".//oscillation_sequence")
        osc_seq = {
            "start": float(osc_seq_node.find(".//start").text),
            "range": float(osc_seq_node.find(".//range").text),
            "number_of_images": float(osc_seq_node.find(".//number_of_images").text),
            "exposure_time": float(osc_seq_node.find(".//exposure_time").text),
            "number_of_passes": float(osc_seq_node.find(".//number_of_passes").text),
        }
        return osc_seq

    def getAxisChoice(self):
        ax = self.root.find(".//axisChoice").text
        return ax.lower()

    def getOtherAxis(self):
        val = float(self.root.find(".//otherAxis").text)
        return val

    def getKappa(self):
        return float(self.root.find(".//kappa").text)

    def getChi(self):
        return float(self.root.find(".//chi").text)

    def getTwoTheta(self):
        return float(self.root.find(".//twoTheta").text)

    def getSampleDetectorDistance(self):
        return float(self.root.find(".//sampleDetectorDistanceInMM").text)

    def getTransmission(self):
        return float(self.root.find(".//transmissionInPerCent").text)

    def getResolution(self):
        return float(self.root.find(".//resolution").text)
