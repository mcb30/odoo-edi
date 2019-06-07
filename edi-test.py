#!/usr/bin/env python3

"""Execute EDI document(s)

Send and/or receive EDI documents directly from the command line, in
order to test EDI functionality.  Documents will be submitted via the
built-in XML-RPC EDI gateway using the default "files" path.
"""

import sys
import os.path
import argparse
import xmlrpc.client
import base64

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument('-v', '--verbose', action='count', default=0,
                    help="Increase verbosity")
parser.add_argument('-o', '--output', default=os.path.curdir,
                    help="Output directory")
parser.add_argument('-t', '--path', default='files', help="EDI gateway path")
parser.add_argument('-n', '--dummy', action='store_true',
                    help="Do not process EDI documents")
parser.add_argument('-s', '--server', default='http://localhost:8069',
                    help="Server URI")
parser.add_argument('-d', '--database', default='odoo', help="Database name")
parser.add_argument('-u', '--username', default='admin', help="User name")
parser.add_argument('-p', '--password', default='admin', help="Password")
parser.add_argument('inputs', nargs='+', help="Input files")
args = parser.parse_args()

# Construct list of input attachments
inputs = []
for filename in args.inputs:
    with open(filename, 'rb') as f:
        inputs.append({
            'name': os.path.basename(filename),
            'data': base64.b64encode(f.read()),
        })

# Construct XML-RPC client
common = xmlrpc.client.ServerProxy(args.server + '/xmlrpc/common')
models = xmlrpc.client.ServerProxy(args.server + '/xmlrpc/2/object')

# Authenticate
uid = common.authenticate(args.database, args.username, args.password, {})

# Perform EDI transfer
res = models.execute_kw(
    args.database, uid, args.password, 'edi.gateway', 'xmlrpc_transfer', [[]],
    {
        args.path: inputs,
        'context': {'default_allow_process': not args.dummy}
    },
)

# List created documents
if args.verbose >= 1 and res['docs']:
    print('\n'.join(x['name'] for x in res['docs']))

# Show any errors
if res.get('errors'):
    sys.exit('\n'.join(x['name'] for x in res['errors']))

# Save output attachments
for output in res[args.path]:
    filename = os.path.basename(output['name'])
    if args.verbose >= 1:
        print(filename)
    with open(os.path.join(args.output, filename), 'xb') as f:
        f.write(base64.b64decode(output['data']))
