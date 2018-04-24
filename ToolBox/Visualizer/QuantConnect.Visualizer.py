"""
Usage:
    QuantConnect.Visualizer.py DATAFILE PLOTFILE [--size height,width]
    QuantConnect.Visualizer.py DATAFILE CSVFILE PLOTFILE [--size height,width]

Arguments:
    DATAFILE   path or filename to the zipped data file to plot.
    CSVFILE   specific CSV file to plot from an option or future file.
    PLOTFILE  path or filename for the output plot.

Options:
    -h --help                         show this.
    -s, --size height,width           plot size in pixels [default: 800,400].
"""

import json
import os
import sys
from clr import AddReference
from pathlib import Path

import matplotlib as mpl

mpl.use('Agg')

import matplotlib.pyplot as plt
from docopt import docopt
from matplotlib.dates import DateFormatter

COLOR_PALETTE = ['#f5ae29', '#657584', '#b1b9c3', '#222222']


def get_assemblies_folder():
    """
    Checks if the path given in the config.json file contains the needed assemblies, if so it returns the
    absolute path to that folder.
    :return: The absolute path to the folder where the needed assemblies are located.
    """
    with open('config.json') as json_data:
        assemblies_folder_info = Path(json.load(json_data)['assembly_folder'])
    assemblies = [file.name for file in assemblies_folder_info.glob('QuantConnect*.*')]
    if 'QuantConnect.ToolBox.exe' not in assemblies or 'QuantConnect.Common.dll' not in assemblies:
        raise NotImplementedError("Please set up correctly the QuantConnect assemblies folder.")
    assembly_folder_path = str(assemblies_folder_info.resolve().absolute())

    config_file = assemblies_folder_info.joinpath('config.json')
    if not config_file.exists():
        cfg_content = {'plugin-directory': assembly_folder_path}
        with open(str(config_file.resolve().absolute()), 'w') as cfg:
            json.dump(cfg_content, cfg)

    return assembly_folder_path


def get_data(zip_file_path, is_tick_data, csv_filename=None):
    """
    It retrieves the data for a given zip file and an optional internal filename for option and futures.
    :param zip_file_path: The path to the zip file whose data we want to plot.
    :param is_tick_data: boolean indicating if the data has tick resolution.
    :param csv_filename: (optional) internal file for the futures and option cases.
    :return: a pandas.DataFrame with the data to plot.
    """
    if csv_filename is not None:
        zip_file_path += '#' + csv_filename

    df = parse_data_as_dataframe(zip_file_path)
    if is_tick_data:
        cols_to_plot = [col for col in df.columns if 'price' in col]
    else:
        cols_to_plot = [col for col in df.columns if 'close' in col]
    cols_to_plot = cols_to_plot[:2] if len(cols_to_plot) == 3 else cols_to_plot
    df = df.loc[:, cols_to_plot]
    return df


def parse_data_as_dataframe(zip_file_path):
    """
    Makes use of the Lean's Toolbox Visualizer to parse the data as pandas.DataFrame.
    :param zip_file_path: the path to the file we want to plot.
    :return: a dataframe with the complete data for that file.
    """
    assemblies_folder = get_assemblies_folder()
    os.chdir(assemblies_folder)
    sys.path.append(assemblies_folder)
    AddReference("QuantConnect.ToolBox")
    from QuantConnect.ToolBox.Visualizer import Visualizer

    vsz = Visualizer(zip_file_path)
    df = vsz.ParseDataFrame()
    return df.loc[df.index.levels[0][0]]


def plot_and_save_image(data, plot_filename, is_low_resolution_data, size_px):
    """
    Plots the data and saves the plot as a png image.
    :param data: a pandas.DataFrame with the data to plot.
    :param plot_filename: the output image file path and name.
    :param is_low_resolution_data: boolean indicating if the data has daily or hourly resolution.
    :param size_px: an array with the size of the image in pixels.
    :return: void
    """
    plot = data.plot(grid=True, color=COLOR_PALETTE)
    fig = plot.get_figure()
    if not is_low_resolution_data:
        plot.xaxis.set_major_formatter(DateFormatter("%H:%M"))

    fig.set_size_inches(size_px[0] / fig.dpi, size_px[1] / fig.dpi)
    fig.savefig(f'{plot_filename}.png', transparent=True, dpi=fig.dpi)


def main(arguments):
    """
    Main entry point.
    :param arguments: docopt dictionary with the arguments.
    :return: void
    """
    if arguments['DATAFILE'] is None or arguments['PLOTFILE'] is None:
        raise NotImplementedError("Please set at minimum an zip data file path and a output image file path.")
    if 'openinterest' in arguments['DATAFILE']:
        raise NotImplementedError("Open interest not supported, yet.")
    zip_file_info = Path(arguments['DATAFILE'])
    zip_file_path = str(zip_file_info.absolute())
    plot_filename = str(Path(arguments['PLOTFILE']).absolute())

    size_px = [int(p) for p in arguments['--size'].split(',')]

    full_path_list = list(zip_file_info.absolute().parts)
    is_low_resolution_data = 'hour' in full_path_list or 'daily' in full_path_list
    is_tick_data = 'tick' in full_path_list

    df = get_data(zip_file_path, is_tick_data, arguments['CSVFILE'])
    plot_and_save_image(df, plot_filename, is_low_resolution_data, size_px)


if __name__ == "__main__":
    arguments = docopt(__doc__)
    main(arguments)
    sys.exit(0)
