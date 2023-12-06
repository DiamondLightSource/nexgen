# CHANGELOG



## 0.7.3

### Added
- Added possibility to write `end_time_estimated` field in NXmxWriter and refactored `write_NXdatetime`.
- A small utility to write a nexus file for electron diffraction and a new command line tool for SINGLA without phil.
- Choice to avoid using the meta file for I19-2 data, as long as all relevant information is passed.
- Utilities to extract collection start time and exposure time from singla master file for ED. 

### Changed
- (Temporary) Write a soft link for /entry/instrument/detector/detector_z in NXdetector, for compatibility with autoPROC.
- Beamline parameters and elettron diffraction have been tidied up.



## 0.7.2

### Added
- Re-added a hasConfig and read_config_dset to Metafile.
- Flag to use config instead of dectris group when updating axes from meta.

### Fixed
- I19 eiger writer to use config when updating axes values.
- I19 eiger writer to read scan axis.


## 0.7.1


**BROKEN!**


## 0.7.0

### Added
- Choise of filter to use for write_compressed_copy
- VDS writer for JungFrau 1M use case.

### Changed
- Refactoring of serial writer.
- Refactoring of I19 writers.
- Refactoring of ED writer.
- Unified logging for beamline tools.
- write_NXdetector now uses a blosc filter to write mask and flatfield for event data.

### Fixed
- SSX cli import issue.
- I19 cli bugs.
- Read params from GDA-generated JSON files.
- Tidy up/clear up obsolete methods.
- Update and fix documentation.

## 0.6.28

### Added
- Jungfrau detector definition.

### Changed
- Source type for ED now set to `Electron Source`.
- Goniometer updated at definition if a scan is passed.

## 0.6.27

### Changed
- VDS clean up of unused links in NXmxFileWriter is now optional and set to False by default. It should only be set to True if positive that all the files have already been written.

## 0.6.26

### Fixed
- Temporary fix to have `bit_depth_readout` link to the correct value in Eiger meta file.

## 0.6.25

### Added
- Method looking up `bit_depth_image` in Eiger meta file.
- Definition of vds dtype using information in `bit_depth_image`.

### Fixed
- Correct links in NeXus file for ssx.
- VDS dtype for ssx.

## 0.6.24

### Added
- Initial set up of new tools for refactoring:
    - Definitions for Goniometer, Detector, Source and Axes.
    - New writer for NXmx and NXmx-like NeXus files which will substitute the old ones.
    - New scan utilities for calculations to work better with scanspec.

### Changed
- VDS writer can now create a dataset from just a subset of data, using starting offset and desired size.

## 0.6.23

### Changed
- Open metafile with ``swmr=True`` to enable reading during data collection
- Read metafile config items from ``/_dectris/`` rather than ``/config/`` as the former should be accessible when read in SWMR mode during data collection

## 0.6.22

### Added
- Added python3.11 support.

### Changed
- Fixed the data file list generation for SSX Eiger so that it doesn't need the files to exist yet.
- Removed python3.7 support.

## 0.6.21

### Added
- Conversion table for SSX chip from coordinates to block number.
- Check and fix for older SSX Tristan datasets which have det_z/distance saved as bytes.

### Fixed
- Oscillation axis end positions being automatically set to 0 instead of metafile value for upwards blocks in SSX chip.

## 0.6.20

### Added
- New function in CopyTristanNexus to deal with serial crystallography data.
- Tests for SSX experiment functions.

### Changed
- Refactoring of I24_Eiger into SSX_Eiger in order to have just one common tool to more beamlines for ssx collections.
- Updated `compute_ssx_axes` in the copy tools to deal with older Tristan SSX datasets.
- Tidying up of SSX_Tristan.
- Removed ssx from I19-2 cli.

### Fixed
- In CopyTristanNexus, `single_image_nexus` now takes number of bins for a static pump-probe experiment as input instead of a flag.

## 0.6.19

### Changed
- In CopyTristanNexus, added a flag to the single_image writer to be able to correctly write a list of values for a static pump-probe collection (ie. the same phi/omega value repeated for each bin).

### Fixed
- Start position for "up" blocks in SSX chip goniometer computation.
- End position for "up" blocks for I24 SSX chip for scanspec hack.

## 0.6.18

### Added
- Temporary messy hotfix to have ssx experiments run on I19-2 with an Eiger detector. To be replaced by mergine with I24 script.

### Changed
- Fixed the hdf5plugin.Bitshuffle deprecation warning when writing a compressed mask with LZ4 filter. For the moment, hdf5plugin version pinned to 4.0.1 minimum.
- Refactoring of the I19-2 command line interface.

## 0.6.17

### Fixed
- VDS writer for datasets that have maximum number of frames set.
- Removed lgtm alerts (obsolete as of 12/2022) and updated some information.

## 0.6.16

### Added
- NXdetector test.
- Output optional argument to the ED parser in case the NeXus file needs to be saved in a different location than the data files.

### Changed
- Chipmap set to None if the inut value from the beamline is "fullchip", indicating that the whole chip is being scanned. The reason for this change is that
the mapping lite is not used when the fullchip option is selected on the beamline and consequently the chipmap file is not updated.
- In VDS_tools.split_datasets(), checks if the dataset is actually used in the VDS before adding it to the list so that unused datasets are not used as sources for the VDS.

### Fixed
- Ensure that the detector distance is always saved in meters and the unit is correct.
- Fix sample_depends_on on I19-2 cli.

## 0.6.15

### Added
- Function to calculate the beam center for Electron Diffraction.
- Add relative tests.

## 0.6.14

### Added
- Phil parameter to override instrument name if not at synchrotron eg. for electron diffraction.
- Function to work out the value of "/entry/instrument/name" so that it's not hard coded.
- Datasets for eventual details in write_NXsample.
- Function to identify a chipmap inside a Tristan NeXus file for grid scans.
- Function to define the axes positions during a SSX Tristan collection. When multiple windows are binned in the same image, the determination of the (x,y)positions on the chip becomes difficult and could lead to misunderstanding. Thus, instead of sam_x and sam_y the number of windows per bin will be saved as NXnote in "/entry/data/windows_per_image".

### Changed
- Instrument name not hard coded anymore in write_NXinstrument.
- Quick explanation in docs for electron diffraction.
- Parameter files for Electron Diffraction.
- CopyTristanNexus can now write a NXmx format NeXus file for binned images from a grid scan collection.

## 0.6.13

### Added
- requirements.txt file.
- readthedocs and codecov config files.

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
