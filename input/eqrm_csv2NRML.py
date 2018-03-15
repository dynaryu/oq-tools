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

import sys
import argparse
from lxml import etree
from csv import DictReader
import pandas as pd

NRML_NS = 'http://openquake.org/xmlns/nrml/0.5'
#GML_NS = 'http://www.opengis.net/gml'
NRML = "{%s}" % NRML_NS
# GML = "{%s}" % GML_NS
NSMAP = {None: NRML_NS}

ROOT = "%snrml" % NRML
# GML_ID = "%sid" % NRML
EXPOSURE_MODEL = "%sexposureModel" % NRML
# CONFIG = "%sconfig" % NRML
# EXPOSURE_LIST = "%sexposureList" % NRML

# Exposure List attributes names
#AREA_TYPE = 'areaType'
#AREA_UNIT = 'areaUnit'
#ASSET_CATEGORY = 'category'
#COCO_TYPE = 'cocoType'
#COCO_UNIT = 'cocoUnit'
#RECO_TYPE = 'recoType'
#RECO_UNIT = 'recoUnit'
#STCO_TYPE = 'stcoType'
#STCO_UNIT = 'stcoUnit'

DESCRIPTION = '%sdescription' % NRML
TAXONOMY_SOURCE = '%staxonomySource' % NRML

# Asset definition tagnames
ASSET = "%sasset" % NRML
#SITE = "%ssite" % NRML
#GML_POINT = "%sPoint" % NRML
#GML_SRS_ATTR_NAME = 'srsName'
#GML_SRS_EPSG_4326 = 'epsg:4326'
#GML_POS = "%spos" % NRML
#AREA = '%sarea' % NRML
#COCO = '%scoco' % NRML
#DEDUCTIBLE = '%sdeductible' % NRML
#LIMIT = '%slimit' % NRML
#NUMBER = '%snumber' % NRML
OCCUPANTS = '%soccupancies' % NRML
#RECO = '%sreco' % NRML
#STCO = '%sstco' % NRML
#TAXONOMY = '%staxonomy' % NRML

NO_VALUE = ''

BLDG_MAPPING = pd.read_csv(
    '/Users/hyeuk/Projects/scenario_Guildford/input/bldg_class_mapping.csv')
BLDG_MAPPING.set_index('NEXIS_CONS', inplace=True)
BLDG_MAPPING = BLDG_MAPPING['MAPPING2'].to_dict()


def convert_to_float(string):
    val = string.split('-')[-1]
    try:
        float(val)
        return float(val)
    except ValueError:
        return None


def map_vul_class(ga_class, year_built, BLDG_MAPPING):

    year = convert_to_float(year_built)

    if BLDG_MAPPING[ga_class][:2] in ['UR', 'W1', 'W2']:

        if year <= 1946:
            tail = 'Pre1945'
        else:
            tail = 'Post1945'

    else:
        if year <= 1996:
            tail = 'Pre1996'
        else:
            tail = 'Post1996'

    return '{}_{}'.format(ga_class, tail)


class ExposureTxtReader(object):

    # ASSETS_FIELDNAMES = ['lon', 'lat', 'taxonomy', 'stco', 'number' ,'area',
    #                      'reco', 'coco', 'occupantDay', 'occupantNight',
    #                      'deductible', 'limit']

    EQRM_FIELDNAMES = [
        'LID', 'LATITUDE', 'LONGITUDE', 'GCC_CODE', 'SA1_CODE', 'LGA_CODE',
        'LGA_NAME', 'SUBURB', 'POSTCODE', 'HAZUS_STRUCTURE_CLASSIFICATION',
        'GA_STRUCTURE_CLASSIFICATION', 'STRUCTURE_CATEGORY', 'HAZUS_USAGE',
        'FCB_USAGE', 'SITE_CLASS', 'YEAR_BUILT', 'CONTENTS_COST_DENSITY',
        'BUILDING_COST_DENSITY', 'FLOOR_AREA', 'POPULATION', 'SURVEY_FACTOR']

    def __init__(self, metadata_file, txtfile):
        self.txtfile = txtfile
        self.metadata_file = metadata_file

    def _move_to_beginning_file_input(self):
        self.txtfile.seek(0)

    def _move_to_beginning_file_meta(self):
        self.metadata_file.seek(0)

    def _move_to_assets_definitions(self):
        self._move_to_beginning_file_input()
        while True:
            line = set([field.strip() for field in (
                self.txtfile.readline()).split(',')])
            if set(self.EQRM_FIELDNAMES).issubset(line):
                break;

    @property
    def metadata(self):
        self._move_to_beginning_file_meta()
        fieldnames = [field.strip() for field in (
            self.metadata_file.readline()).split(',')]
        fieldvalues = [value.strip() for value in (
            self.metadata_file.readline()).split(',')]
        return dict(zip(fieldnames, fieldvalues))

    def readassets(self):
        self._move_to_assets_definitions()
        reader = DictReader(self.txtfile, fieldnames=self.EQRM_FIELDNAMES)
        return [asset for asset in reader]


class ExposureWriter(object):

    def serialize(self, filename, metadata, assets):
        root_elem = self._write_header(metadata)
        root_elem = self._write_assets(root_elem, assets)
        tree = etree.ElementTree(root_elem)
        with open(filename, 'w') as output_file:
            tree.write(output_file, xml_declaration=True,
                encoding='utf-8', pretty_print=True)
        # to_csv
        _df = pd.DataFrame(assets)
        _df.set_index('LID', inplace=True)
        _df[['SA1_CODE', 'SUBURB', 'REPL_COST', 'POPULATION']].to_csv('{}.csv'.format(filename))

    def _value_defined_for(self, dict, attrib):
        return dict[attrib] != NO_VALUE

    def _write_header(self, metadata):
        root_elem = etree.Element(ROOT, nsmap=NSMAP)
        exp_mod_elem = etree.SubElement(root_elem, EXPOSURE_MODEL)
        exp_mod_elem.attrib['id'] = metadata['expModId']
        if self._value_defined_for(metadata, 'category'):
            exp_mod_elem.attrib['category'] = metadata['category']
        else:
            raise RuntimeError('assetCategory is a compulsory value')
        if self._value_defined_for(metadata, 'taxonomySource'):
            exp_mod_elem.attrib['taxonomySource'] = metadata['taxonomySource']

        if self._value_defined_for(metadata, 'description'):
            desc_elem = etree.SubElement(exp_mod_elem, 'description')
            desc_elem.text = metadata['description']

        conv_elem = etree.SubElement(exp_mod_elem, 'conversions')

        cost_elem = etree.SubElement(conv_elem, 'costTypes')
        stco_elem = etree.SubElement(cost_elem, 'costType')
        stco_elem.attrib['name'] = 'structural'
        stco_elem.attrib['type'] = metadata['stcoType']
        stco_elem.attrib['unit'] = metadata['stcoUnit']

        # if self._value_defined_for(metadata, 'cocoType'):
        #     coco_elem = etree.SubElement(cost_elem, 'costType')
        #     coco_elem.attrib['name'] = 'contents'
        #     coco_elem.attrib['type'] = metadata['cocoType']
        #     coco_elem.attrib['unit'] = metadata['cocoUnit']

        # if self._value_defined_for(metadata, 'stcoUnit'):
        # if self._value_defined_for(metadata, 'cocoType'):
        #     cost_elem.attrib[COCO_TYPE] = metadata['cocoType']
        # if self._value_defined_for(metadata, 'cocoUnit'):
        #     cost_elem.attrib[COCO_UNIT] = metadata['cocoUnit']
        # if self._value_defined_for(metadata, 'recoType'):
        #     cost_elem.attrib[RECO_TYPE] = metadata['recoType']
        # if self._value_defined_for(metadata, 'recoUnit'):
        #     cost_elem.attrib[RECO_UNIT] = metadata['recoUnit']

        area_elem = etree.SubElement(conv_elem, 'area')
        area_elem.attrib['type'] = metadata['areaType']
        area_elem.attrib['unit'] = metadata['areaUnit']

        return root_elem

    def _write_assets(self, root_elem, assets):
        exp_mod_elem = root_elem.find('.//%s' % EXPOSURE_MODEL)
        exp_list = etree.SubElement(exp_mod_elem, 'assets')
        for asset in assets:
            asset_elem = etree.SubElement(exp_list, ASSET)
            asset_elem.attrib['id'] = asset['LID']
            asset_elem.attrib['taxonomy'] = map_vul_class(
                asset['GA_STRUCTURE_CLASSIFICATION'],
                asset['YEAR_BUILT'], BLDG_MAPPING)
            # asset['TAXONOMY'] = asset_elem.attrib['taxonomy']
            asset_elem.attrib['area'] = asset['FLOOR_AREA']
            asset_elem.attrib['number'] = '1'

            if (self._value_defined_for(asset, 'LONGITUDE') and
                self._value_defined_for(asset, 'LATITUDE')):

                site_elem = etree.SubElement(
                    asset_elem, 'location')
                site_elem.attrib['lon'] = asset['LONGITUDE']
                site_elem.attrib['lat'] = asset['LATITUDE']
            else:
                raise RuntimeError('lon and lat are compulsory values for an '
                                   'asset')

            cost_elem = etree.SubElement(asset_elem, 'costs')
            if self._value_defined_for(asset, 'BUILDING_COST_DENSITY'):
                stco_elem = etree.SubElement(cost_elem, 'cost')
                stco_elem.attrib['type'] = 'structural'
                repl_cost = (float(asset['BUILDING_COST_DENSITY']) +
                             float(asset['CONTENTS_COST_DENSITY']))
                stco_elem.attrib['value'] = '{}'.format(repl_cost)
                asset['REPL_COST'] = repl_cost * float(asset['FLOOR_AREA'])

            if self._value_defined_for(asset, 'POPULATION'):
                occupants_elem = etree.SubElement(
                    asset_elem, OCCUPANTS)
                occupants_night_elem = etree.SubElement(
                    occupants_elem, 'occupancy')
                occupants_night_elem.attrib['occupants'] = asset['POPULATION']
                occupants_night_elem.attrib['period'] = 'night'

        return root_elem


def cmd_parser():

    parser = argparse.ArgumentParser(prog='exposureTxt2NRML')

    parser.add_argument('-m', '--metadata-file',
        nargs=1,
        metavar='metadata file',
        dest='metadata_file',
        help='metadata file corresponding to the input file')

    parser.add_argument('-i', '--input-file',
        nargs=1,
        metavar='input file',
        dest='input_file',
        help='Specify the input file (i.e. exposure.txt)')

    parser.add_argument('-o', '--output-file',
        nargs=1,
        metavar='output file',
        dest='output_file',
        default=['exposure_portfolio.xml'],
        help='Specify the output file (i.e. exposure_portfolio.xml)')

    parser.add_argument('-v', '--version',
        action='version',
        version="%(prog)s 0.0.1")

    return parser

def main():

    parser = cmd_parser()
    if len(sys.argv) == 1:
        parser.print_help()
    else:
        args = parser.parse_args()
        with open(args.metadata_file[0]) as metadata_file, \
                open(args.input_file[0]) as input_file:
            reader = ExposureTxtReader(metadata_file, input_file)
            metadata = reader.metadata
            assets = reader.readassets()

        writer = ExposureWriter()
        writer.serialize(args.output_file[0], metadata, assets)

if __name__ == '__main__':
    main()
