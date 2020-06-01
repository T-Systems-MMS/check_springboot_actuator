About check_springboot_actuator
===============================

This is an Nagios/Icinga check plugin for
[Spring Boot](https://projects.spring.io/spring-boot/) applications using the
[actuator framework](http://docs.spring.io/spring-boot/docs/current-SNAPSHOT/reference/htmlsingle/#production-ready).
The check inspects the response from the health and metrics endpoints.

Usage
========
Example:
```
./check_springboot_actuator.py -U "http://localhost:14041/testservice/v1/actuator" -N --th "metric=testservice_files_in_failure_value,ok=0,warning=1..20,critical=20.." -m testservice.files.in.failure
```

Features
========

The check checks the status field from the health endpoint for

- global status
- cassandra status
- diskSpace status
- db
- dataSource status
- elasticsearch status
- jms status
- mail status
- mongo status
- rabbit status
- redis status
- solr status
- vault

The check aggregates metrics for the counter.status data from the metrics
endpoints.

License
=======

check_springboot_actuator is licensed under the terms of the MIT license as
described in the LICENSE file.

Requirements
============

check_springboot_actuator requires Python 2.7 and the pynag and requests
libraries in the versions specified in requirements.txt.
