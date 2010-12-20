"""CGI/FastCGI handler for Mapnik OGC WMS Server.

Requires 'jon' module.

"""

from os import environ
from tempfile import gettempdir
environ['PYTHON_EGG_CACHE'] = gettempdir()

import sys
from jon import cgi

from ogcserver.common import Version
from ogcserver.configparser import SafeConfigParser
from ogcserver.wms111 import ExceptionHandler as ExceptionHandler111
from ogcserver.wms130 import ExceptionHandler as ExceptionHandler130
from ogcserver.exceptions import OGCException, ServerConfigurationError

class Handler(cgi.DebugHandler):

    def __init__(self, home_html=None):
        conf = SafeConfigParser()
        conf.readfp(open(self.configpath))
        # TODO - be able to supply in config as well
        self.home_html = home_html
        self.conf = conf
        if not conf.has_option_with_value('server', 'module'):
            raise ServerConfigurationError('The factory module is not defined in the configuration file.')
        try:
            mapfactorymodule = __import__(conf.get('server', 'module'))
        except ImportError:
            raise ServerConfigurationError('The factory module could not be loaded.')
        if hasattr(mapfactorymodule, 'WMSFactory'):
            self.mapfactory = getattr(mapfactorymodule, 'WMSFactory')()
        else:
            raise ServerConfigurationError('The factory module does not have a WMSFactory class.')
        if conf.has_option('server', 'debug'):
            self.debug = int(conf.get('server', 'debug'))
        else:
            self.debug = 0

    def process(self, req):
        base = False
        if not req.params:
            base = True

        reqparams = lowerparams(req.params)
        server_port = req.environ['SERVER_PORT']
        if server_port == '80':
            port = ''
        else:
            port = ':%s' % server_port
        onlineresource = 'http://%s%s%s?' % (req.environ['SERVER_NAME'], port, req.environ['SCRIPT_NAME'])

        try:
            if not reqparams.has_key('request'):
                raise OGCException('Missing request parameter.')
            request = reqparams['request']
            del reqparams['request']
            if request == 'GetCapabilities' and not reqparams.has_key('service'):
                raise OGCException('Missing service parameter.')
            if request in ['GetMap', 'GetFeatureInfo']:
                service = 'WMS'
            else:
                service = reqparams['service']
            if reqparams.has_key('service'):
                del reqparams['service']
            try:
                ogcserver = __import__('ogcserver.' + service)
            except:
                raise OGCException('Unsupported service "%s".' % service)
            ServiceHandlerFactory = getattr(ogcserver, service).ServiceHandlerFactory
            servicehandler = ServiceHandlerFactory(self.conf, self.mapfactory, onlineresource, reqparams.get('version', None))
            if reqparams.has_key('version'):
                del reqparams['version']
            if request not in servicehandler.SERVICE_PARAMS.keys():
                raise OGCException('Operation "%s" not supported.' % request, 'OperationNotSupported')
            ogcparams = servicehandler.processParameters(request, reqparams)
            try:
                requesthandler = getattr(servicehandler, request)
            except:
                raise OGCException('Operation "%s" not supported.' % request, 'OperationNotSupported')

            # stick the user agent in the request params
            # so that we can add ugly hacks for specific buggy clients
            ogcparams['HTTP_USER_AGENT'] = req.environ['HTTP_USER_AGENT']

            response = requesthandler(ogcparams)
        except:
            version = reqparams.get('version', None)
            if not version:
                version = Version()
            else:
                version = Version(version)
            if version >= '1.3.0':
                eh = ExceptionHandler130(self.debug,base,self.home_html)
            else:
                eh = ExceptionHandler111(self.debug,base,self.home_html)
            response = eh.getresponse(reqparams)

        req.set_header('Content-Type', response.content_type)
        req.set_header('Content-Length', str(len(response.content)))
        req.write(response.content)

    def traceback(self, req):
        reqparams = lowerparams(req.params)
        version = reqparams.get('version', None)
        if not version:
            version = Version()
        else:
            version = Version(version)
        if version >= '1.3.0':
            eh = ExceptionHandler130(self.debug)
        else:
            eh = ExceptionHandler111(self.debug)
        response = eh.getresponse(reqparams)
        req.set_header('Content-Type', response.content_type)
        req.set_header('Content-Length', str(len(response.content)))
        req.write(response.content)

def lowerparams(params):
    reqparams = {}
    for key, value in params.items():
        reqparams[key.lower()] = value
    return reqparams