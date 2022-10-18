# CHANGELOG

##

### Added
- Function to write a compressed copy of a dataset in a specified NXgroup. Main application: mask and flatfield in NXdetector.
- General conversion to mcstas from a user defined coordinate frame.
- NXcoordinate_system_set writer.

### Changed
- Entry key for data in NXdata as argument.
- Rotation axis for the detector not hard coded to two theta anymore.

---
## 0.6.11

### Added
- Blank template for .phil files.

### Fixed
- Plugin for Mask and Flatfield copy/compress/write to NeXus.


---
## 0.6.10

### Added
- Method to read `config/` dataset from a metafile.
- Functions to update goniometer or detector axes positions directly from the `config` dataset.
- Ability to specify non-zero indexed VDS.
- New cli for I19-2 NeXus writer - it can now work with and without GDA-generated metadata.
- Docstrings for namedtuples in beamline scripts.
- Show phil parameters using `--show-config` from the command line. 

### Changed
- SSX chip reading tools moved to SSX_chip.py
- Moved GDA tools to beamlines.
- SSX Tristan writer can now also be called from I24.
- Save a "chipmap" in a dataset for SSX Tristan collections instead of the total number of city blocks.
- Merged old write_nexus functions from scope_extract into one.

### Fixed
- Data size order - always (slow, fast).
- Axes datasets always saved as arrays instead of SCALAR.
- Improved scan axis calculations.
- Fixed copy functions so that new file has a different name from original.