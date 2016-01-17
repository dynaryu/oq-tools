#!/usr/bin/python

"""
Reads hazard map in NRML format and converts it to shapefile.
Supports NRML format 0.3.
Required libraries are:
- lxml
- pyshp
"""

import sys
import argparse
import shapefile
from lxml import etree


def set_up_arg_parser():
    """
    Set up command line parser.
    """
    parser = argparse.ArgumentParser(description='Convert NRML format hazard map file to shapefile.'\
                    'To run just type: python hazardMapNRML2Shapefile.py --hazard-map-file=/PATH/HAZARD_MAP_FILE_NAME.xml')
    parser.add_argument('--hazard-map-file', help='path to NRML hazard map file', default=None)
    return parser


def parse_hazard_map_file(hazard_map_file):
    """
    Parse NRML hazard map file.
    """
    parse_args = dict(source=hazard_map_file)

    lons = []
    lats = []
    data = []

    for _, element in etree.iterparse(**parse_args):

        if element.tag.find('node') > 0:
            for e in element.iter():
                lons.append(float(e.get('lon')))
                lats.append(float(e.get('lat')))
                data.append(float(e.get('iml')))

    return lons, lats, data


def serialize_data_to_shapefile(lons, lats, data, file_name):
    """
    Serialize hazard map data to shapefile.
    """

    w = shapefile.Writer(shapefile.POINT)
    w.field('VALUE', 'N', 10, 5)

    for i in range(len(data)):
        w.point(lons[i], lats[i], 0, 0)
        w.record(round(data[i], 5))
    w.save(file_name)

    print 'Shapefile saved to: %s.shp' % file_name


def main(argv):
    """
    Parse command line argument and performs requested action.
    """
    parser = set_up_arg_parser()
    args = parser.parse_args()

    if args.hazard_map_file:
        lons, lats, data = parse_hazard_map_file(args.hazard_map_file)
        serialize_data_to_shapefile(lons, lats, data, args.hazard_map_file.rstrip('.xml'))
    else:
        parser.print_help()

if __name__ == '__main__':

    main(sys.argv)
