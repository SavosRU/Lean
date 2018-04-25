"""
Usage:
    QuantConnect.Visualizer.py DATAFILE [--output file_path] [--size height,width]

Arguments:
    DATAFILE   Absolute or relative path to a zipped data file to plot.
               Optionally the zip entry file can be declared by using '#' as separator.
    PLOTFILE   Path or filename for the output plot.

Options:
    -h --help                 show this.
    -o --output file_path     path or filename for the output plot. If not declared, it will save with an
                              auto-generated name at the default folder defined in the config.json file.
    -s, --size height,width   plot size in pixels [default: 800,400].

Examples:
    QuantConnect.Visualizer.py ../relative/path/to/file.zip
    QuantConnect.Visualizer.py absolute/path/to/file.zip#zipEntry.csv
"""

import json
import os
import sys
import uuid
from clr import AddReference
from pathlib import Path

import matplotlib as mpl

mpl.use('Agg')

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


def get_data(data_file_argument):
    """
    It retrieves the data for a given zip file and an optional internal filename for option and futures.
    :param data_file_argument: Absolute or relative path to a zipped data file to plot, optionally the zip entry file
                               can be declared by using '#' as separator.
    :return: a pandas.DataFrame with the data to plot.
    """
    df = parse_data_as_dataframe(data_file_argument)
    if 'tick' in data_file_argument:
        cols_to_plot = [col for col in df.columns if 'price' in col]
    else:
        cols_to_plot = [col for col in df.columns if 'close' in col]

    if 'openinterest' in data_file_argument:
        cols_to_plot = ['openinterest']

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


def generate_plot_filename():
    """
    Generates a random name for the output plot image file in the default folder defined in the config.json file.
    :return: an absolute path to the output plot image file.
    """
    with open('config.json') as json_data:
        default_output_folder = Path(json.load(json_data)['default_output_folder'])

    if not default_output_folder.exists():
        os.makedirs(str(default_output_folder.resolve().absolute()))
    file_name = f'{str(uuid.uuid4())[:8]}.png'
    file_path = default_output_folder.joinpath(file_name)
    return str(file_path.resolve().absolute())


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
    fig.savefig(plot_filename, transparent=True, dpi=fig.dpi)


def get_data_plot_and_save_image(arguments):
    """
    Get the data from a zipped file, make the plot, saves and returns the plot absolute path.
    :param arguments: dictionary with the CLI arguments.
    :return: the absolute file path to the output plot
    """
    data_file_argument = arguments['DATAFILE']

    if data_file_argument is None:
        raise NotImplementedError("Please set at minimum a zipped data file path.")

    plot_filename = arguments['--output']
    if plot_filename is None:
        plot_filename = generate_plot_filename()

    df = get_data(data_file_argument)
    size_px = [int(p) for p in arguments['--size'].split(',')]
    is_low_resolution_data = 'hour' in data_file_argument or 'daily' in data_file_argument

    plot_and_save_image(df, plot_filename, is_low_resolution_data, size_px)
    return plot_filename


if __name__ == "__main__":
    arguments = docopt(__doc__)
    print(get_data_plot_and_save_image(arguments))
    sys.exit(0)
