# CHANGELOG

##

### Added
- Phil parameter to override instrument name if not at synchrotron eg. for electron diffraction.
- Function to work out the value of "/entry/instrument/name" so that it's not hard coded.
- Datasets for eventual details in write_NXsample.

### Changed
- Instrument name not hard coded anymore in write_NXinstrument.
- Quick explanation in docs for electron diffraction.
- Parameter files for Electron Diffraction.

## 0.6.13

### Added
- requirements.txt file
- readthedocs and codecov config files

### Changed
- Refactoring of split_arrays and reframe_arrays: split arrays now does just that - splitting into size-3 tuples. Everything else, in particulare the conversion from other coordinate systems, is taken care of by reframe_arrays.
- Chip definition in SSX tools.
- WORKAROUND: Define end position of goniometer for a 2d scan (fixed target) on I24 as (end - increment) to avoind scanspec miscalculating the scan values.

### Fixed
- Cast n_exposures for I24 fixed target experiment to int.


---
## 0.6.12

### Added
- NeXus writer function, phil template and parameter file for Electron Diffraction data.
- CLI for Electron Diffraction.
- Function to write a compressed copy of a dataset in a specified NXgroup. Main application: mask and flatfield in NXdetector.
- General conversion to mcstas from a user defined coordinate frame.
- NXcoordinate_system_set writer.
- Multiple exposures for fixed-target scan in I24 writer. (Issue [#75](https://github.com/dials/nexgen/issues/75) opened to discuss VDS possibilities.)
- Tests for NXentry, NXcoordinate_system_set and NXnote writers.
- Tests for SSX chip tools.
- Tests for Metafile tools and ElectronDiffraction tools.

### Changed
- Entry key for data in NXdata as argument.
- Rotation axis for the detector not hard coded to two theta anymore.
- Splitting of arrays done before feeding the goniometer/detector dictionaries to the NXclass writers.
- All conversions to mcstas done before passing vectors/arrays to writers.

### Fixed
- Outstanding data_size order issues.
- Sample depends_on bug in NXsample writer: the value can now be passed as input argument to write_NXsample. If absent, it will default to the last axis in the goniometer list.


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