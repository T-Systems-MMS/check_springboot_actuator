#!/usr/bin/env python
from __future__ import print_function

import logging

from pynag.Plugins import PluginHelper, ok, critical, unknown
from requests import get
from requests.exceptions import ConnectionError

helper = PluginHelper()

helper.parser.add_option(
    '-U', '--url',
    help='Base URL of Spring Boot Application (default: %default)',
    dest='url', default='http://localhost:8080')
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
        return get(url, **get_args).json(), None
    except ConnectionError as e:
        helper.debug('error fetching data from {}'.format(url))
        return None, e
    finally:
        logging.captureWarnings(False)


json_data, err = request_data(health_endpoint, **get_args)

if json_data is None:
    if err is None:
        helper.status(unknown)
        helper.add_summary('no health data available')
    else:
        helper.status(critical)
        helper.add_summary('could not fetch health data: {}'.format(err))
else:
    status = json_data['status']
    if status == 'UP':
        helper.status(ok)
    elif status in ('DOWN', 'OUT_OF_SERVICE'):
        helper.status(critical)
    else:
        helper.status(unknown)
    helper.add_summary('global status is {}'.format(status))

    for item in [
        'cassandra', 'diskSpace', 'dataSource', 'elasticsearch', 'jms', 'mail',
        'mongo', 'rabbit', 'redis', 'solr'
    ]:
        if item in json_data:
            item_status = json_data[item]['status']
            helper.add_summary('{} status is {}'.format(item, item_status))
            if helper.get_status() != critical and item_status == 'UNKNOWN':
                helper.status(unknown)
            elif item_status in ('DOWN', 'OUT_OF_SERVICE'):
                helper.status(critical)

json_data, err = request_data(metrics_endpoint, **get_args)

if json_data is None:
    if err is None:
        helper.add_summary('no metrics data available')
    else:
        helper.add_summary('error fetching metrics data: {}'.format(err))
else:
    http_status_counter = {}

    for key in json_data:
        if key.startswith('counter.status'):
            status = key.split('.', 4)[2]
            http_status_counter[status] = (
                http_status_counter.get(status, 0) + json_data[key])
        else:
            helper.add_metric(label=key.replace('.', '_'), value=json_data[key])

    for status in http_status_counter:
        helper.add_metric(
            label='http{}'.format(status), value=http_status_counter[status])

helper.exit()
