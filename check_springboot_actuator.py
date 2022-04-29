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
helper.parser.add_option(
    '-m', '--metrics',
    help='comma separated list of metrics to display',
    dest='metrics')
helper.parser.add_option(
    '-u', '--user-credentials',
    help='user credentials in the format username:password',
    dest='credentials')

helper.parse_arguments()

health_endpoint = helper.options.url + '/health'
metrics_endpoint = helper.options.url + '/metrics'

contenttype_v1 = 'application/vnd.spring-boot.actuator.v1'
contenttype_v2 = 'application/vnd.spring-boot.actuator.v2'
contenttype_v3 = 'application/vnd.spring-boot.actuator.v3'

get_args = {'verify': helper.options.verify}

if helper.options.truststore:
    get_args['verify'] = helper.options.truststore

if helper.options.credentials:
    get_args['auth'] = tuple(helper.options.credentials.split(':'))


def request_data(url, **get_args):
    """executes get request to retrieve data from given url"""
    logging.captureWarnings(True)
    try:
        response = get(url, **get_args)
        # check response content type to determine which actuator api to be used
        if response.ok or response.status_code == 503:
            contenttype = response.headers['Content-Type']
            if contenttype.startswith('application/vnd.spring-boot'):
                version = 1 
                if contenttype.startswith(contenttype_v2): version = 2
                elif contenttype.startswith(contenttype_v3): version = 3
                return response.json(), version, None
            else:
                return None, None, Exception(response.status_code, url)
        else:
            return None, None, Exception(response.status_code, url)
    except ConnectionError as e:
        helper.debug('error fetching data from {}'.format(url))
        return None, None, e
    finally:
        logging.captureWarnings(False)


def handle_version_1():
    """handles metrics from spring boot 1.x application"""
    json_data, _, err = request_data(metrics_endpoint, **get_args)

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


def handle_version_2():
    """handles metrics from spring boot 2.x application"""
    metrics = []
    if helper.options.metrics:
        metrics = helper.options.metrics.split(',')

    http_status_counter = {}
    for key in metrics:
        key = key.strip()
        json_data, _, err = request_data(metrics_endpoint + "/" + key, **get_args)

        if err:
            helper.add_summary('error fetching metrics data: {}'.format(err))
            break

        measurements = json_data['measurements']
        for measurement in measurements:
            if key.startswith('counter.status'):
                status = key.split('.', 4)[2]
                http_status_counter[status] = (
                        http_status_counter.get(status, 0) + measurement['value'])
            else:
                helper.add_metric(label="%s_%s" % (key.replace('.', '_'), measurement['statistic'].lower()), value=measurement['value'])


    for status in http_status_counter:
        helper.add_metric(
            label='http{}'.format(status), value=http_status_counter[status])


json_data, version, err = request_data(health_endpoint, **get_args)
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


    details = json_data
    if version == 2:
        details = json_data['status']
    if version == 3 and 'components' in json_data :
        details = json_data['components'] 

    for item in [
        'cassandra', 'diskSpace', 'dataSource', 'elasticsearch', 'jms', 'mail',
        'mongo', 'rabbit', 'redis', 'solr', 'db', 'vault', 'livenessState',
        'readinessState', 'ping', 'couchbase', 'hazelcast', 'influxdb', 'ldap', 'neo4j'
    ]:
        if item in details:
            item_status = details[item]['status']
            helper.add_summary('{} status is {}'.format(item, item_status))
            if helper.get_status() != critical and item_status == 'UNKNOWN':
                helper.status(unknown)
            elif item_status in ('DOWN', 'OUT_OF_SERVICE'):
                helper.status(critical)

    if version == 1:
        handle_version_1()
    if version == 2:
        handle_version_2()

helper.exit()
