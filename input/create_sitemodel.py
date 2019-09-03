# Copyright (c) 2010-2012, GEM Foundation.
#
# exposureTxt2NRML is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# exposureTxt2NRML is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with exposureTxt2NRML.  If not, see <http://www.gnu.org/licenses/>.
"""
exposureTxt2NRML creates an exposure input file format (NRML)
taking an exposure portfolio in a fixed txt format.
"""

import os
import sys
import math
import argparse
from lxml import etree
from csv import DictReader

NRML_NS = 'http://openquake.org/xmlns/nrml/0.5'
GML_NS = 'http://www.opengis.net/gml'
NRML = "{%s}" % NRML_NS
GML = "{%s}" % GML_NS
NSMAP = {None: NRML_NS, "gml": GML_NS}

ROOT = "%snrml" % NRML
GML_ID = "%sid" % GML
SITE_MODEL = "%ssiteModel" % NRML
SITE_LIST = "%ssite" % NRML

# SITE List attributes names
VS30 = 'vs30'
LON = 'lon'
LAT = 'lat'
Z1PT0 = 'z1pt0'
Z2PT5 = 'z2pt5'
VS30TYPE = 'vs30Type'

NO_VALUE = ''


def create_z1pt0_z2pt5_dic():

    _dic = {}
    for value in [115, 180, 270, 412, 560, 760, 1100]:

        z1pt0, z2pt5 = est_z1pt0_z2pt5_given_v30(value)
        _dic[value] = {'z1pt0': z1pt0, 'z2pt5': z2pt5}

    return _dic


def est_z1pt0_z2pt5_given_v30(vs30):

    # CHIOU and YOUNGS (2014)
    a = math.pow(vs30, 4) + math.pow(571, 4)
    b = math.pow(1360, 4) + math.pow(571, 4)
    z1pt0 = math.exp(-7.15/4.0*math.log(a/b))  # in m

    # KAKLAMANOS et al. (2011)
    z2pt5 = 0.001 * (519 + 3.59 * z1pt0)  # m -> km

    return z1pt0, z2pt5


class SiteModelTxtReader(object):

    SITES_FIELDNAMES = ['lon', 'lat', 'vs30']

    def __init__(self, txtfile):
        self.txtfile = txtfile

    def _move_to_beginning_file(self):
        self.txtfile.seek(0)

    def _move_to_assets_definitions(self):
        self._move_to_beginning_file()
        while True:
            line = set([field.strip() for field in (
                self.txtfile.readline()).split(',')])
            if set(self.SITES_FIELDNAMES).issubset(line):
                break;

    @property
    def metadata(self):
        self._move_to_beginning_file()
        fieldnames = [field.strip() for field in (
            self.txtfile.readline()).split(',')]
        fieldvalues = [value.strip() for value in (
            self.txtfile.readline()).split(',')]
        return dict(zip(fieldnames, fieldvalues))

    def readassets(self):
        self._move_to_assets_definitions()
        reader = DictReader(self.txtfile, fieldnames=self.SITES_FIELDNAMES)
        return [asset for asset in reader]


class SiteModelWriter(object):

    def serialize(self, filename, metadata, assets):
        root_elem = self._write_header(metadata)
        root_elem = self._write_assets(root_elem, assets)
        tree = etree.ElementTree(root_elem)
        with open(filename, 'w') as output_file:
            tree.write(output_file, xml_declaration=True,
                encoding='utf-8', pretty_print=True)

    def _value_defined_for(self, dict, attrib):
        return dict[attrib] != NO_VALUE

    def _write_header(self, metadata):
        root_elem = etree.Element(ROOT, nsmap=NSMAP)
        #root_elem.attrib[GML_ID] = 'n1'
        exp_mod_elem = etree.SubElement(
            root_elem, SITE_MODEL)
        #exp_mod_elem.attrib[GML_ID] = 'ep1'
        # config = etree.SubElement(
        #     exp_mod_elem, CONFIG)
        # exp_list_elem = etree.SubElement(
        #      exp_mod_elem, SITE_LIST)
        # exp_list_elem.attrib[GML_ID] = metadata['expModId']
        # if self._value_defined_for(metadata, 'vs30'):
        #     exp_list_elem.attrib[VS30_TYPE] = metadata['vs30']
        # if self._value_defined_for(metadata, 'lon'):
        #     exp_list_elem.attrib[LON_TYPE] = metadata['lon']
        # if self._value_defined_for(metadata, 'lat'):
        #     exp_list_elem.attrib[LAT_TYPE] = metadata['lat']

        return root_elem

    def _write_assets(self, root_elem, assets):
        exp_list = root_elem.find('.//%s' % SITE_MODEL)
        for i, asset in enumerate(assets, start=1):
            asset_elem = etree.SubElement(exp_list, SITE_LIST)
            asset_elem.attrib[LON] = '%s' % asset['lon'].strip()
            asset_elem.attrib[LAT] = '%s' % asset['lat'].strip()
            asset_elem.attrib[VS30] = '%s' % asset['vs30'].strip()
            asset_elem.attrib[VS30TYPE] = 'inferred'

            vs30 = int(float(asset['vs30']))
            try:
                _dic = z1pt0_z2pt5_dic[vs30]
            except KeyError:
                z1pt0, z2pt5 = est_z1pt0_z2pt5_given_v30(vs30)
            else:
                z1pt0, z2pt5 = _dic['z1pt0'], _dic['z2pt5']

            asset_elem.attrib[Z1PT0] = '{}'.format(z1pt0)
            asset_elem.attrib[Z2PT5] = '{}'.format(z2pt5)
            asset_elem.attrib['backarc'] = 'false'

        return root_elem

z1pt0_z2pt5_dic = create_z1pt0_z2pt5_dic()


def cmd_parser():

    parser = argparse.ArgumentParser(prog='site_model2NRML')

    parser.add_argument('-i', '--input-file',
        nargs=1,
        metavar='input file',
        dest='input_file',
        help='Specify the input file (i.e. site_model.csv)')

    return parser

def main():

    parser = cmd_parser()

    if len(sys.argv) == 1:
        parser.print_help()
    else:
        args = parser.parse_args()
        with open(args.input_file[0]) as input_file:
            reader = SiteModelTxtReader(input_file)
            metadata = reader.metadata
            assets = reader.readassets()

        _path = os.path.abspath(os.path.dirname(args.input_file[0]))
        _list = os.path.basename(args.input_file[0]).split('.')
        output_file = os.path.join(_path, '{}.xml'.format(_list[0]))

        writer = SiteModelWriter()
        writer.serialize(output_file, metadata, assets)

if __name__ == '__main__':
    main()
