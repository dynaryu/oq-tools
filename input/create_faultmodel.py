"""
exposureTxt2NRML creates an exposure input file format (NRML)
taking an exposure portfolio in a fixed txt format.
"""

import sys
import os
import argparse
from lxml import etree

NRML_NS = 'http://openquake.org/xmlns/nrml/0.5'
GML_NS = 'http://www.opengis.net/gml'
NRML = "{%s}" % NRML_NS
GML = "{%s}" % GML_NS
NSMAP = {None: NRML_NS, "gml": GML_NS}

ROOT = "%snrml" % NRML
RUPTURE = "%ssinglePlaneRupture" % NRML
MAG = "%smagnitude" % NRML
RAKE = "%srake" % NRML
HYPOCENTER = "%shypocenter" % NRML
PLANARSURFACE = "%splanarSurface" %NRML
TOPLEFT = "%stopLeft" %NRML
TOPRIGHT = "%stopRight" %NRML
BOTTOMLEFT = "%sbottomLeft" %NRML
BOTTOMRIGHT = "%sbottomRight" %NRML

map_dic = {TOPLEFT: 'top_left',
           TOPRIGHT: 'top_right',
           BOTTOMRIGHT: 'bottom_right',
           BOTTOMLEFT: 'bottom_left'}

NO_VALUE = ''


class EventTxtReader(object):

    def __init__(self, txtfile):
        self.txtfile = txtfile

    def _move_to_beginning_file(self):
        self.txtfile.seek(0)

    @property
    def metadata(self):
        self._move_to_beginning_file()
        fieldnames = [field.strip() for field in (
            self.txtfile.readline()).split(',')]
        fieldvalues = [value.strip() for value in (
            self.txtfile.readline()).split(',')]
        return dict(zip(fieldnames, fieldvalues))


class RuptureWriter(object):

    def serialize(self, filename, metadata):
        root_elem = self._write_header(metadata)
        tree = etree.ElementTree(root_elem)
        with open(filename, 'w') as output_file:
            tree.write(output_file, xml_declaration=True,
                encoding='utf-8', pretty_print=True)

    def _value_defined_for(self, dict, attrib):
        return dict[attrib] != NO_VALUE

    def _write_header(self, metadata):
        root_elem = etree.Element(ROOT, nsmap=NSMAP)

        rupture_elem = etree.SubElement(root_elem, RUPTURE)

        mag_elem = etree.SubElement(rupture_elem, MAG)
        mag_elem.text = metadata['Mw']

        rake_elem = etree.SubElement(rupture_elem, RAKE)
        rake_elem.text = metadata['rake']

        hypocenter_elem = etree.SubElement(rupture_elem, HYPOCENTER)
        hypocenter_elem.attrib['lat'] = metadata['rupture_centroid_lat']
        hypocenter_elem.attrib['lon'] = metadata['rupture_centroid_lon']
        hypocenter_elem.attrib['depth'] = metadata['depth']

        surface_elem = etree.SubElement(rupture_elem, PLANARSURFACE)
        surface_elem.attrib['strike'] = metadata['azimuth']
        surface_elem.attrib['dip'] = metadata['dip']

        for item in [TOPLEFT, TOPRIGHT, BOTTOMLEFT, BOTTOMRIGHT]:
            _cnr = etree.SubElement(surface_elem, item)
            _cnr.attrib['lon'] = metadata['{}_longitude'.format(map_dic[item])]
            _cnr.attrib['lat'] = metadata['{}_latitude'.format(map_dic[item])]
            _cnr.attrib['depth'] = metadata['{}_depth'.format(map_dic[item])]

        return root_elem


def cmd_parser():

    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input-file',
        nargs=1,
        metavar='input file',
        dest='input_file',
        help='Specify the input file (i.e. exposure.txt)')

    return parser


def main():

    parser = cmd_parser()
    if len(sys.argv) == 1:
        parser.print_help()
    else:
        args = parser.parse_args()
        with open(args.input_file[0]) as input_file:
            reader = EventTxtReader(input_file)
            metadata = reader.metadata

        _path = os.path.abspath(os.path.dirname(args.input_file[0]))
        _list = os.path.basename(args.input_file[0]).split('.')
        output_file = os.path.join(_path, '{}.xml'.format(_list[0]))

        writer = RuptureWriter()
        writer.serialize(output_file, metadata)


if __name__ == '__main__':
    main()
