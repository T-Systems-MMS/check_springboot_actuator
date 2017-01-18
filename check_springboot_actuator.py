#!/usr/bin/env python
from __future__ import print_function

import logging

from pynag.Plugins import PluginHelper, ok, critical, unknown
from requests import get
from requests.exceptions import SSLError

helper = PluginHelper()

helper.parser.add_option(
    '-U', '--url',
    help='Base URL of Spring Boot Application (default: %default)',
    dest='url', default='http://localhost:8080/')
helper.parser.add_option(
    '-N', '--no-check-certificate',
    help="don't verify certificate", dest='verify',
    action='store_false', default=True)
helper.parser.add_option(
    '-t', '--trust-store',
    help='trust store (PEM format) to use for TLS certificate validation',
    dest='truststore')

helper.parse_arguments()

health_endpoint = helper.options.url + '/health/'
metrics_endpoint = helper.options.url + '/metrics/'

get_args = {'verify': helper.options.verify}

if helper.options.truststore:
    get_args['verify'] = helper.options.truststore


def request_data(url, **get_args):
    logging.captureWarnings(True)
    try:
        return get(url, **get_args).json()
    except SSLError:
        logging.exception('error fetching data from %s', url)
        return None
    finally:
        logging.captureWarnings(False)


json_data = request_data(health_endpoint, **get_args)

if json_data is None:
    helper.status(unknown)
    helper.add_summary('no health data available')
else:
    status = json_data['status']
    if status == 'UP':
        helper.status(ok)
    elif status in ('DOWN', 'OUT_OF_SERVICE'):
        helper.status(critical)
    else:
        helper.status(unknown)
    helper.add_summary('global status is ' + status)

    for item in [
        'diskSpace', 'cassandra', 'diskSpace', 'dataSource', 'elasticsearch',
        'jms', 'mail', 'mongo', 'rabbit', 'redis', 'solr'
    ]:
        if item in json_data:
            item_status = json_data[item]['status']
            helper.add_summary('{} status is {}'.format(item, item_status))
            if helper.get_status() != critical and item_status == 'UNKNOWN':
                helper.status(unknown)
            elif item_status in ('DOWN', 'OUT_OF_SERVICE'):
                helper.status(critical)

json_data = request_data(metrics_endpoint, **get_args)

if json_data is None:
    helper.status(unknown)
    helper.add_summary('no metrics data available')
else:
    http_status_counter = {}

    for key in json_data:
        if key.startswith('counter.status'):
            status = key.split('.', 4)[2]
            http_status_counter[status] = (
                http_status_counter.get(status, 0) + json_data[key])

    for status in http_status_counter:
        helper.add_metric(
            label='http' + status, value=http_status_counter[status])

helper.exit()
