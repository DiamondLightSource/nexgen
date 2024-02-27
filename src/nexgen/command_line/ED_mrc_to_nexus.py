import mrcfile
import os
import h5py
import numpy as np
from math import sqrt
from nexgen.nxs_utils import Attenuator, Beam, Detector, Goniometer
from nexgen.nxs_utils import CetaDetector
from nexgen.nxs_write.NXmxWriter import EDNXmxFileWriter
from nexgen.beamlines.ED_params import ED_coord_system, EDCeta, EDSource
from nexgen.nxs_utils.ScanUtils import calculate_scan_points
from pathlib import Path
from argparse import ArgumentParser
import hdf5plugin


def main():

    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        "--det_distance",
        type=float,
        default=None,
        help="The sample-detector distance.",
    )
    parser.add_argument(
        "-wl",
        "--wavelength",
        type=float,
        default=None,
        help="Incident beam wavelength, in A.",
    )
    parser.add_argument(
        "--axis-start",
        type=float,
        default=None,
        help="Rotation axis start position.",
    )
    parser.add_argument(
        "--axis-inc",
        type=float,
        default=None,
        help="Rotation axis increment.",
    )
    parser.add_argument(
        "-e",
        "--exp-time",
        type=float,
        help="Exposure time, in s.",
    )
    parser.add_argument(
        "-bc",
        "--beam-center",
        type=float,
        nargs=2,
        help="Beam center (x,y) positions.",
    )
    parser.add_argument('input_files', nargs='+', help='List of input files')

    args = parser.parse_args()

    for file in args.input_files:
        if not file.endswith('.mrc'):
            raise ValueError('Not an mrc file!')

    mrc_files = args.input_files
    tot_imgs, out_file, angles = collect_data(mrc_files)
    mdict = get_metadata(mrc_files[0])

    attenuator = Attenuator(transmission=None)

    if args.det_distance is not None:
        det_distance = args.det_distance
    else:
        det_distance = mdict['cameraLength']
    if args.wavelength is not None:
        beam = Beam(args.wavelength)
    else:
        beam = Beam(mdict['wavelength'])
    if args.axis_start is not None:
        start_angle = args.axis_start
    else:
        start_angle = angles[0]
    if args.axis_inc is not None:
        increment = args.axis_inc
    else:
        increment = mdict['tiltPerImage']
    if args.exp_time is not None:
        exposure_time = args.exp_time
    else:
        exposure_time = mdict['integrationTime']
    if args.beam_center is not None:
        if len(args.beam_center) == 2:
            x, y = args.beam_center
            beam_center = (x, y)
        else:
            msg = 'Beam center requires two arguments'
            raise ValueError(msg)
    else:
        beam_center = (mdict["beamCentreXpx"],
                       mdict["beamCentreYpx"])

    gonio_axes = EDCeta.gonio
    gonio_axes[0].start_pos = start_angle
    gonio_axes[0].increment = increment
    gonio_axes[0].num_steps = tot_imgs

    scan = calculate_scan_points(gonio_axes[0],
                                 rotation=True,
                                 tot_num_imgs=tot_imgs)
    goniometer = Goniometer(gonio_axes, scan)
    osc, trans = goniometer.define_scan_from_goniometer_axes()

    nx = mdict['nx']
    ny = mdict['ny']

    if (nx == 2048) and (ny == 2048):
        binning = 2
    else:
        binning = 1

    det_params = CetaDetector("Thermo Fisher Ceta-D", [nx, ny])

    pixel_size = 0.014 * binning
    ps_str = '%5.3fmm' % pixel_size
    det_params.pixel_size = [ps_str, ps_str]
    det_params.overload = 8000 * binning**2

    extra_params = {}
    mask = np.zeros((nx, ny), dtype=np.int32)
    flatfield = np.ones((nx, ny), dtype=np.float32)
    extra_params['pixel_mask'] = mask
    extra_params['flatfield'] = flatfield
    extra_params['pixel_mask_applied'] = 1
    extra_params['flatfield_applied'] = 1
    det_params.constants.update(extra_params)

    det_axes = EDCeta.det_axes

    det_axes[0].start_pos = det_distance

    detector = Detector(det_params, det_axes, beam_center,
                        exposure_time,
                        [EDCeta.fast_axis,
                         EDCeta.slow_axis])

    source = EDSource
    source.beamline = 'Ceta'

    script_dir = os.getcwd()
    file_name = out_file.replace('h5', 'nxs')
    full_path = os.path.join(script_dir, file_name)
    data_path = os.path.join(script_dir, out_file)
    data_path = Path(data_path)

    writer = EDNXmxFileWriter(
         full_path,
         goniometer,
         detector,
         source,
         beam,
         attenuator,
         tot_imgs,
         ED_coord_system)

    datafiles = [data_path]
    writer.write(datafiles, '/entry/data/data')
    writer.write_vds(vds_dtype=np.int32,
                     datafiles=datafiles)


def get_metadata(mrc_image):

    print('Opening ', mrc_image)
    with mrcfile.open(mrc_image, header_only=True) as mrc:
        h = mrc.header
        try:
            xh = mrc.indexed_extended_header
        except AttributeError:
            # For mrcfile versions older than 1.5.0
            xh = mrc.extended_header
        hd = {}

        hd['nx'] = h['nx']
        hd['ny'] = h['ny']
        hd['nz'] = h['nz']
        hd['mx'] = h['mx']
        hd['my'] = h['my']
        hd['mz'] = h['mz']

        hd["alphaTilt"] = xh["Alpha tilt"][0]
        hd["integrationTime"] = xh["Integration time"][0]
        hd["tilt_axis"] = xh["Tilt axis angle"][0]
        hd["pixelSpacing"] = xh["Pixel size X"][0]
        hd["acceleratingVoltage"] = xh["HT"][0]
        hd["camera"] = xh["Camera name"][0]
        hd["binning"] = xh["Binning Width"][0]
        hd["noiseReduction"] = xh["Ceta noise reduction"][0]
        hd["physicalPixel"] = 14e-6
        hd["wavelength"] = cal_wavelength(hd["acceleratingVoltage"])
        hd["cameraLength"] = (hd["physicalPixel"] * hd["binning"]
                              ) / (hd["pixelSpacing"]
                                   * hd["wavelength"] * 1e-10) * 1000.
        hd["scanRotation"] = xh["Scan rotation"][0]
        hd["diffractionPatternRotation"] = xh[
            "Diffraction pattern rotation"][0]
        hd["imageRotation"] = xh["Image rotation"][0]
        hd["scanModeEnum"] = xh["Scan mode enumeration"][0]
        hd["acquisitionTimeStamp"] = xh["Acquisition time stamp"][0]
        hd["detectorCommercialName"] = xh["Detector commercial name"][0]
        hd["startTiltAngle"] = xh["Start tilt angle"][0]
        hd["endTiltAngle"] = xh["End tilt angle"][0]
        hd["tiltPerImage"] = xh["Tilt per image"][0]
        hd["tiltSpeed"] = xh["Tilt speed"][0]
        hd["beamCentreXpx"] = xh["Beam center X pixel"][0]
        hd["beamCentreYpx"] = xh["Beam center Y pixel"][0]
        hd["cfegFlashTimestamp"] = xh["CFEG flash timestamp"][0]
        hd["phasePlatePositionIndex"] = xh["Phase plate position index"][0]
        hd["objectiveApertureName"] = xh["Objective aperture name"][0]

        # Check if binning is correct
        assert hd['binning'] == 4096 / hd['nx']

        return hd


def cal_wavelength(V0):
    h = 6.626e-34  # Js, Planck's constant
    m = 9.109e-31  # kg, electron mass
    e = 1.6021766208e-19  # C, electron charge
    c = 3e8  # m/s^2, speed

    # Default to e-wavelength at 200 keV if voltage set to zero
    if V0 == 0:
        V0 = 200000
    wlen = h / sqrt(2*m*e*V0 * (1 + e*V0 / (2*m*c*c))) * 1e10
    return wlen       # return wavelength in Angstrom


def collect_data(files):

    out_file = files[0].rsplit('_', 1)[0] + '.h5'
    mrc_files = []
    angles = []
    for file in files:
        path = os.path.abspath(file)
        if path.endswith('.mrc'):
            mrc_files.append(file)

    n = len(mrc_files)

    test_file = mrcfile.open(mrc_files[0], mode='r')
    data_shape = test_file.data.shape
    test_file.close()
    if len(data_shape) != 2:
        msg = 'The converter works only with single mrc images'
        raise ValueError(msg)

    with h5py.File(out_file, 'w') as hdf5_file:
        dataset_shape = (n, data_shape[0], data_shape[1])
        dataset = hdf5_file.create_dataset('data_temp',
                                           shape=dataset_shape,
                                           dtype=np.int32)

        group = hdf5_file.create_group("entry")
        group.attrs["NX_class"] = np.string_('NXentry')
        data_group = group.create_group('data')
        data_group.attrs["NX_class"] = np.string_("NXdata")

        compressed_data = hdf5_file.create_dataset('/entry/data/data',
                                                   shape=dataset_shape,
                                                   dtype=np.int32,
                                                   **hdf5plugin.LZ4())

        for i, file in enumerate(mrc_files):
            print('%0.2d  %s' % (i, file))
            mrc = mrcfile.open(file, mode='r')
            data = np.array(mrc.data, dtype=np.int32)
            try:
                xh = mrc.indexed_extended_header
            except AttributeError:
                xh = mrc.extended_header

            angles.append(xh["Alpha tilt"][0])
            dataset[i, :, :] = data
            mrc.close()

        compressed_data[...] = dataset[...]
        del hdf5_file['data_temp']

        return n, out_file, np.array(angles)
