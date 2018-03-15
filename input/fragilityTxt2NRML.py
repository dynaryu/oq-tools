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
fragilityTxt2NRML creates a fragility input file format (NRML)
taking a fragility in a fixed txt format.
"""

import sys
import argparse
from lxml import etree

NRML_NS = 'http://openquake.org/xmlns/nrml/0.5'
#GML_NS = 'http://www.opengis.net/gml'
NRML = "{%s}" % NRML_NS
#GML = "{%s}" % GML_NS
NSMAP = {None: NRML_NS}

ROOT = "%snrml" % NRML
#GML_ID = "%sid" % GML
#CONFIG = "%sconfig" % NRML

# Fragility tagnames

FRAGILITY_MOD = '%sfragilityModel' % NRML
FRAG_FUN = '%sfragilityFunction' % NRML
IML = '%simls' % NRML
POES = '%spoes' % NRML

# Fragility attributes

ID = 'id'
ASSET_CAT = 'assetCategory'
LOSS_CAT = 'lossCategory'
IMT = 'imt'

NO_VALUE = ''


class FragilityTxtReader(object):

    FST_LINE_FIELDNAMES = ['fragilityModelID', 'assetCategory',
                           'lossCategory', 'description']
    SND_LINE_FIELDNAME = 'limitStates'

    def __init__(self, txtfile):
        self.txtfile = txtfile
        self.no_limitstates = 0

    def _move_to_beginning_file(self):
        self.txtfile.seek(0)

    def _move_to_dscr_frag_def(self):
        # It assumes that discreteFragility definitions
        # start from 4th line, so it's necessary to skip
        # the first three lines.
        self._move_to_beginning_file()
        lines_to_skip = 3
        for i in xrange(0, lines_to_skip):
            self.txtfile.readline()

    def _acquire_frag_lines(self):
        lines = []
        for line in self.txtfile:
            lines.append(line.strip())
        print(len(lines))
        if len(lines) % (2 + self.no_limitstates) != 0:
            raise RuntimeError('Every fragility is composed by {:d} '
                               'lines'.format(2 + self.no_limitstates))
        return lines

    @property
    def metadata(self):
        self._move_to_beginning_file()
        fst_line_values = [field.strip() for field in
                           (self.txtfile.readline()).split(',')]
        metadata = dict(zip(self.FST_LINE_FIELDNAMES, fst_line_values))
        snd_line_values = [field.strip() for field in
                               (self.txtfile.readline()).split(',')]
        metadata[self.SND_LINE_FIELDNAME] = snd_line_values
        self.no_limitstates = len(snd_line_values)
        return metadata

    def readfragility(self):
        self._move_to_dscr_frag_def()
        lines = self._acquire_frag_lines()
        definitions = []
        for i in xrange(0, len(lines), 2 + self.no_limitstates):
            meta_values = lines[i].split(',')
            imt_values = lines[i+1].split(',')
            poe_values = []

            for j in xrange(self.no_limitstates):
                poe_values.append(lines[i + 2 +j].split(','))

            frag_def = dict(
                fragilityFunctionId=meta_values[0],
                frag_format=meta_values[1],
                imt_str=meta_values[2],
                nodamage_limit=meta_values[3],
                imt=imt_values,
                poe=poe_values)

            definitions.append(frag_def)

        return definitions


class FragilityWriter(object):

    def _value_defined_for(self, dict, attrib):
        return dict[attrib] != NO_VALUE

    def serialize(self, filename, metadata, frag_definitions):
        root_elem = self._write_header(metadata)
        root_elem = self._write_frag_def(root_elem, metadata, frag_definitions)
        tree = etree.ElementTree(root_elem)
        with open(filename, 'w') as output_file:
            tree.write(output_file, xml_declaration=True,
                encoding='utf-8', pretty_print=True)

    def _write_header(self, metadata):

        root_elem = etree.Element(ROOT, nsmap=NSMAP)
        frag_mod = etree.SubElement(root_elem, FRAGILITY_MOD)

        if self._value_defined_for(metadata, 'fragilityModelID'):
            frag_mod.attrib[ID] = metadata['fragilityModelID']
        else:
            raise RuntimeError('fragilityModel id is a required attribute, '
                               'a fix to the input file is necessary')

        if self._value_defined_for(metadata, 'assetCategory'):
            frag_mod.attrib[ASSET_CAT] = metadata['assetCategory']
        else:
            raise RuntimeError('assetCategory is a required attribute, '
                               'a fix to the input file is necessary')

        if self._value_defined_for(metadata, 'lossCategory'):
            frag_mod.attrib[LOSS_CAT] = metadata['lossCategory']
        else:
            raise RuntimeError('lossCategory is a required attribute, '
                               'a fix to the input file is necessary')

        description = etree.SubElement(frag_mod, 'description')
        description.text = metadata['description']

        limit_states = etree.SubElement(frag_mod, 'limitStates')
        limit_states.text = ' '.join(metadata['limitStates'])

        return root_elem

    def _write_frag_def(self, root_elem, metadata, frag_definitions):
        frag_set = root_elem.find('.//%s' % FRAGILITY_MOD)
        for frag_def in frag_definitions:
            frag_def_elem = etree.SubElement(frag_set, FRAG_FUN)

            if self._value_defined_for(frag_def, 'fragilityFunctionId'):
                frag_def_elem.attrib[ID] = (frag_def['fragilityFunctionId'])
            else:
                raise RuntimeError('fragilityFunctionID is a required '
                                   'attribute, a fix to the input file is '
                                   'necessary')

            if self._value_defined_for(frag_def, 'frag_format'):
                frag_def_elem.attrib['format'] = (
                    frag_def['frag_format'])
            else:
                raise RuntimeError('fragilityFunction format is a required '
                                   'attribute, a fix to the input file is '
                                   'necessary')

            if frag_def['frag_format'] == 'discrete':
                iml_elem = etree.SubElement(frag_def_elem, IML)
                iml_elem.attrib[IMT] = frag_def['imt_str']
                iml_elem.attrib['noDamageLimit'] = frag_def['nodamage_limit']
                iml_elem.text = ' '.join(frag_def['imt'])

                for i, ds in enumerate(metadata['limitStates']):
                    poes_elem = etree.SubElement(frag_def_elem, 'poes')
                    poes_elem.attrib['ls'] = ds
                    poes_elem.text = ' '.join(frag_def['poe'][i])
            elif frag_def['frag_format'] == 'continuous':
                print('NOT IMPLEMENTED YET')
            else:
                raise RuntimeError('invalid fragilityFunction format {}'.format(frag_def['frag_format']))

        return root_elem


def cmd_parser():

    parser = argparse.ArgumentParser(prog='fragilityTxt2NRML')

    parser.add_argument('-i', '--input-file',
        nargs=1,
        metavar='input file',
        dest='input_file',
        help='Specify the input file (i.e. fragility.txt)')

    parser.add_argument('-o', '--output-file',
        nargs=1,
        metavar='output file',
        dest='output_file',
        default=['fragility_model.xml'],
        help='Specify the output file (i.e. fragility_model.xml)')

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
        with open(args.input_file[0]) as input_file:
            reader = FragilityTxtReader(input_file)
            metadata = reader.metadata
            frag_def = reader.readfragility()
        writer = FragilityWriter()
        writer.serialize(args.output_file[0], metadata, frag_def)

if __name__ == '__main__':
    main()