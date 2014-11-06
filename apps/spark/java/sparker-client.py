#! /usr/bin/env python

import json
import httplib

sparker_client_default_host = 'localhost'
sparker_client_default_port = 8080

class SparkerClient:
    # Configuration
    host = sparker_client_default_host
    port = sparker_client_default_port
    # State
    connection = None
    session_id = None
    output_cursor = 0
    # Constants
    POST = 'POST'
    GET = 'GET'
    ROOT = '/'
    OK = 200
    def __init__(self, host=sparker_client_default_host, port=sparker_client_default_port):
        self.host = host
        self.port = port
        self.connection = self.create_connection()
        self.session_id = self.create_session()
    def http_json(self, method, url, body=''):
        self.connection.request(method, url, body)
        response = self.connection.getresponse()
        if response.status != self.OK:
            raise Exception(str(resonse.status) + ' ' + response.reason)
        response_text = response.read()
        if len(response_text) != 0:
            return json.loads(response_text)
        return ''
    def create_connection(self):
        return httplib.HTTPConnection(self.host, self.port)
    def create_session(self):
        return self.http_json(self.POST, self.ROOT)
    def get_sessions(self):
        return self.http_json(self.GET, self.ROOT)
    def get_session(self):
        return self.http_json(self.GET, self.ROOT + self.session_id)
    def post_input(self, command):
        self.http_json(self.POST, self.ROOT + self.session_id, command)
    def get_output(self):
        output = self.get_session()[self.output_cursor:]
        self.output_cursor += len(output)
        return output
    def close_connection(self):
        self.connection.close()

import threading
import time
import sys

class SparkerPoller(threading.Thread):
    keep_polling = True
    def __init__(self, sparker_client):
        threading.Thread.__init__(self)
        self.sparker_client = sparker_client
    def stop_polling(self):
        self.keep_polling = False
    def run(self):
        while self.keep_polling:
            output = self.sparker_client.get_output()
            for line in output:
                print(line)
            time.sleep(1)

client = SparkerClient()
poller = SparkerPoller(client)
poller.start()

try:
    while True:
        line = raw_input()
        client.post_input(line)
except:
    poller.stop_polling()
    # TODO: delete session?
    client.close_connection()

sys.exit(0)
