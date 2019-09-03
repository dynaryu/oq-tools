"""
exposureTxt2NRML creates an exposure input file format (NRML)
taking an exposure portfolio in a fixed txt format.
"""

import sys
import os
import argparse
from csv import DictReader
from lxml import etree
from shapely.geometry import MultiPolygon
from shapely import wkt

NRML_NS = 'http://openquake.org/xmlns/nrml/0.5'
GML_NS = 'http://www.opengis.net/gml'
NSMAP = {None: NRML_NS, "gml": GML_NS}

NRML = "{%s}" % NRML_NS
GML = "{%s}" % GML_NS
GML_POS = "{%s}posList" % NSMAP['gml']
GML_LINE = "{%s}LineString" % NSMAP['gml']

ROOT = "%snrml" % NRML
RUPTURE = "%ssimpleFaultRupture" % NRML
MAG = "%smagnitude" % NRML
RAKE = "%srake" % NRML
HYPOCENTER = "%shypocenter" % NRML
SIMPLEFAULT = "%ssimpleFaultGeometry" %NRML
DIP = "%sdip" % NRML
UPPER = "%supperSeismoDepth" % NRML
LOWER = "%slowerSeismoDepth" % NRML

NO_VALUE = ''


class RuptureTxtReader(object):

    RUPTURE_FIELDNAMES = ['rupid', 'multiplicity', 'mag', 'centroid_lon', 
                          'centroid_lat', 'centroid_depth', 'trt', 'strike', 
                          'dip', 'rake', 'boundary']

    def __init__(self, txtfile):
        self.txtfile = txtfile

    def _move_to_beginning_file(self):
        self.txtfile.seek(0)

    def _move_to_ruptures_definitions(self):
        self._move_to_beginning_file()
        while True:
            line = set([field.strip() for field in (
                self.txtfile.readline()).split('\t')])
            if set(self.RUPTURE_FIELDNAMES).issubset(line):
                break;

    def readruptures(self):
        self._move_to_ruptures_definitions()
        reader = DictReader(self.txtfile, fieldnames=self.RUPTURE_FIELDNAMES, delimiter='\t')
        return [rupture for rupture in reader]


class RuptureWriter(object):

    def serialize(self, filename, rupture_data):
        root_elem = self._write_header(rupture_data)
        tree = etree.ElementTree(root_elem)
        with open(filename, 'w') as output_file:
            tree.write(output_file, xml_declaration=True,
                encoding='utf-8', pretty_print=True)

    def _value_defined_for(self, dict, attrib):
        return dict[attrib] != NO_VALUE

    def _write_header(self, rupture_data):
        root_elem = etree.Element(ROOT, nsmap=NSMAP)

        rupture_elem = etree.SubElement(root_elem, RUPTURE)

        mag_elem = etree.SubElement(rupture_elem, MAG)
        mag_elem.text = rupture_data['mag']

        rake_elem = etree.SubElement(rupture_elem, RAKE)
        rake_elem.text = rupture_data['rake']

        hypocenter_elem = etree.SubElement(rupture_elem, HYPOCENTER)
        hypocenter_elem.attrib['lat'] = rupture_data['centroid_lat']
        hypocenter_elem.attrib['lon'] = rupture_data['centroid_lon']
        hypocenter_elem.attrib['depth'] = rupture_data['centroid_depth']

        surface_elem = etree.SubElement(rupture_elem, SIMPLEFAULT)
        gml_line = etree.SubElement(surface_elem, GML_LINE)
        gml_pos = etree.SubElement(gml_line, GML_POS)
        poly = wkt.loads(rupture_data['boundary'])
        if len(poly) == 1:
            gml_pos.text = '\n'.join(['{} {}'.format(x, y) for x, y in poly[0].exterior.coords])
        else:
            print('NOT IMPLEMENTED YET')
        dip = etree.SubElement(surface_elem, DIP)
        dip.text = rupture_data['dip']

        upper = etree.SubElement(surface_elem, UPPER)
        upper.text = '0'
        lower = etree.SubElement(surface_elem, LOWER)
        lower.text = '100'

        return root_elem


def cmd_parser():

    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input-file',
        nargs=1,
        metavar='input file',
        dest='input_file',
        help='Specify the input file (i.e. ruptures_524.csv)')

    parser.add_argument('-n', '--rupture-id',
        nargs=1,
        metavar='rupture id',
        dest='rupture_id',
        help='Specify the rupture id (i.e. 87')

    return parser


def main():

    parser = cmd_parser()
    if len(sys.argv) < 3:
        parser.print_help()
    else:
        args = parser.parse_args()
        with open(args.input_file[0]) as input_file:
            reader = RuptureTxtReader(input_file)
            ruptures = reader.readruptures()

        _path = os.path.abspath(os.path.dirname(args.input_file[0]))
        _list = os.path.basename(args.input_file[0]).split('.')
        rup_id = int(args.rupture_id[0])
        output_file = os.path.join(_path, '{}_{}.xml'.format(_list[0], rup_id))

        writer = RuptureWriter()
        writer.serialize(output_file, ruptures[rup_id])

if __name__ == '__main__':
    main()
