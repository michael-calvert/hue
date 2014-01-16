#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import desktop
import desktop.urls
import desktop.conf
import logging
import json
import os
import time

import desktop.views as views
import proxy.conf

from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest
from nose.tools import assert_true, assert_false, assert_equal, assert_not_equal, assert_raises
from django.conf.urls.defaults import patterns, url
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.db.models import query, CharField, SmallIntegerField

from desktop.lib import django_mako
from desktop.lib.django_test_util import make_logged_in_client
from desktop.lib.paginator import Paginator
from desktop.lib.conf import validate_path
from desktop.lib.django_util import TruncatingModel
from desktop.lib.exceptions_renderable import PopupException
from desktop.lib.test_utils import grant_access
from desktop.views import check_config, home
from desktop.models import DocumentTag , Document
from pig.models import PigScript
from useradmin.models import GroupPermission, get_default_user_group


def setup_test_environment():
  """
  Sets up mako to signal template rendering.
  """
  django_mako.render_to_string = django_mako.render_to_string_test
setup_test_environment.__test__ = False

def teardown_test_environment():
  """
  This method is called by nose_runner when
  the tests all finish.  This helps track
  down when tests aren't cleaning up after
  themselves and leaving threads hanging around.
  """
  import threading
  # We should shut down all relevant threads by test completion.
  threads = list(threading.enumerate())

  try:
    import threadframe
    import traceback
    if len(threads) > 1:
      for v in threadframe.dict().values():
        traceback.print_stack(v)
  finally:
    # threadframe is only available in the dev build.
    pass

  assert 1 == len(threads), threads

  django_mako.render_to_string = django_mako.render_to_string_normal
teardown_test_environment.__test__ = False

def test_home():
  c = make_logged_in_client()
  response = c.get(reverse(home))

  assert_equal(200, response.status_code)

def test_skip_wizard():
  c = make_logged_in_client() # is_superuser

  response = c.get('/', follow=True)
  assert_true(['admin_wizard.mako' in _template.filename for _template in response.template], [_template.filename for _template in response.template])

  c.cookies['hueLandingPage'] = 'home'
  response = c.get('/', follow=True)
  assert_true(['home.mako' in _template.filename for _template in response.template], [_template.filename for _template in response.template])

  c.cookies['hueLandingPage'] = ''
  response = c.get('/', follow=True)
  assert_true(['admin_wizard.mako' in _template.filename for _template in response.template], [_template.filename for _template in response.template])


  c = make_logged_in_client(username="test_skip_wizard", password="test_skip_wizard", is_superuser=False)

  response = c.get('/', follow=True)
  assert_true(['home.mako' in _template.filename for _template in response.template], [_template.filename for _template in response.template])

  c.cookies['hueLandingPage'] = 'home'
  response = c.get('/', follow=True)
  assert_true(['home.mako' in _template.filename for _template in response.template], [_template.filename for _template in response.template])

  c.cookies['hueLandingPage'] = ''
  response = c.get('/', follow=True)
  assert_true(['home.mako' in _template.filename for _template in response.template], [_template.filename for _template in response.template])

def test_log_view():
  c = make_logged_in_client()

  URL = reverse(views.log_view)

  LOG = logging.getLogger(__name__)
  LOG.warn('une voix m’a réveillé')

  # UnicodeDecodeError: 'ascii' codec can't decode byte... should not happen
  response = c.get(URL)
  assert_equal(200, response.status_code)

  c = make_logged_in_client()

  URL = reverse(views.log_view)

  LOG = logging.getLogger(__name__)
  LOG.warn('Got response: PK\x03\x04\n\x00\x00\x08\x00\x00\xad\x0cN?\x00\x00\x00\x00')

  # DjangoUnicodeDecodeError: 'utf8' codec can't decode byte 0xad in position 75: invalid start byte... should not happen
  response = c.get(URL)
  assert_equal(200, response.status_code)

def test_download_log_view():
  c = make_logged_in_client()

  URL = reverse(views.download_log_view)

  LOG = logging.getLogger(__name__)
  LOG.warn(u'une voix m’a réveillé')

  # UnicodeDecodeError: 'ascii' codec can't decode byte... should not happen
  response = c.get(URL)
  assert_equal("application/zip", response.get('Content-Type', ''))

def test_dump_config():
  c = make_logged_in_client()

  CANARY = "abracadabra"
  clear = desktop.conf.HTTP_HOST.set_for_testing(CANARY)

  response1 = c.get(reverse('desktop.views.dump_config'))
  assert_true(CANARY in response1.content)

  response2 = c.get(reverse('desktop.views.dump_config'), dict(private="true"))
  assert_true(CANARY in response2.content)

  # There are more private variables...
  assert_true(len(response1.content) < len(response2.content))

  clear()

  CANARY = "(localhost|127\.0\.0\.1):(50030|50070|50060|50075)"
  clear = proxy.conf.WHITELIST.set_for_testing(CANARY)

  response1 = c.get(reverse('desktop.views.dump_config'))
  assert_true(CANARY in response1.content)

  clear()

  # Malformed port per HUE-674
  CANARY = "asdfoijaoidfjaosdjffjfjaoojosjfiojdosjoidjfoa"
  clear = desktop.conf.HTTP_PORT.set_for_testing(CANARY)

  response1 = c.get(reverse('desktop.views.dump_config'))
  assert_true(CANARY in response1.content, response1.content)

  clear()

  CANARY = '/tmp/spacé.dat'
  finish = proxy.conf.WHITELIST.set_for_testing(CANARY)
  try:
    response = c.get(reverse('desktop.views.dump_config'))
    assert_true(CANARY in response.content, response.content)
  finally:
    finish()

  # Login as someone else
  client_not_me = make_logged_in_client(username='not_me', is_superuser=False, groupname='test')
  grant_access("not_me", "test", "desktop")

  response = client_not_me.get(reverse('desktop.views.dump_config'))
  assert_true("You must be a superuser" in response.content, response.content)

  os.environ["HUE_CONF_DIR"] = "/tmp/test_hue_conf_dir"
  resp = c.get(reverse('desktop.views.dump_config'))
  del os.environ["HUE_CONF_DIR"]
  assert_true('/tmp/test_hue_conf_dir' in resp.content, resp)


def test_prefs():
  c = make_logged_in_client()

  # Get everything
  response = c.get('/desktop/prefs/')
  assert_equal('{}', response.content)

  # Set and get
  response = c.get('/desktop/prefs/foo', dict(set="bar"))
  assert_equal('true', response.content)
  response = c.get('/desktop/prefs/foo')
  assert_equal('"bar"', response.content)

  # Reset (use post this time)
  c.post('/desktop/prefs/foo', dict(set="baz"))
  response = c.get('/desktop/prefs/foo')
  assert_equal('"baz"', response.content)

  # Check multiple values
  c.post('/desktop/prefs/elephant', dict(set="room"))
  response = c.get('/desktop/prefs/')
  assert_true("baz" in response.content)
  assert_true("room" in response.content)

  # Delete everything
  c.get('/desktop/prefs/elephant', dict(delete=""))
  c.get('/desktop/prefs/foo', dict(delete=""))
  response = c.get('/desktop/prefs/')
  assert_equal('{}', response.content)

  # Check non-existent value
  response = c.get('/desktop/prefs/doesNotExist')
  assert_equal('null', response.content)

def test_status_bar():
  """
  Subs out the status_bar_views registry with temporary examples.
  Tests handling of errors on view functions.
  """
  backup = views._status_bar_views
  views._status_bar_views = []

  c = make_logged_in_client()
  views.register_status_bar_view(lambda _: HttpResponse("foo", status=200))
  views.register_status_bar_view(lambda _: HttpResponse("bar"))
  views.register_status_bar_view(lambda _: None)
  def f(r):
    raise Exception()
  views.register_status_bar_view(f)

  response = c.get("/desktop/status_bar")
  assert_equal("foobar", response.content)

  views._status_bar_views = backup


def test_paginator():
  """
  Test that the paginator works with partial list.
  """
  def assert_page(page, data, start, end):
    assert_equal(page.object_list, data)
    assert_equal(page.start_index(), start)
    assert_equal(page.end_index(), end)

  # First page 1-20
  obj = range(20)
  pgn = Paginator(obj, per_page=20, total=25)
  assert_page(pgn.page(1), obj, 1, 20)

  # Second page 21-25
  obj = range(5)
  pgn = Paginator(obj, per_page=20, total=25)
  assert_page(pgn.page(2), obj, 21, 25)

  # Handle extra data on first page (22 items on a 20-page)
  obj = range(22)
  pgn = Paginator(obj, per_page=20, total=25)
  assert_page(pgn.page(1), range(20), 1, 20)

  # Handle extra data on second page (22 items on a 20-page)
  obj = range(22)
  pgn = Paginator(obj, per_page=20, total=25)
  assert_page(pgn.page(2), range(5), 21, 25)

  # Handle total < len(obj). Only works for QuerySet.
  obj = query.QuerySet()
  obj._result_cache = range(10)
  pgn = Paginator(obj, per_page=10, total=9)
  assert_page(pgn.page(1), range(10), 1, 10)

  # Still works with a normal complete list
  obj = range(25)
  pgn = Paginator(obj, per_page=20)
  assert_page(pgn.page(1), range(20), 1, 20)
  assert_page(pgn.page(2), range(20, 25), 21, 25)

def test_thread_dump():
  c = make_logged_in_client()
  response = c.get("/desktop/debug/threads")
  assert_true("test_thread_dump" in response.content)

def test_truncating_model():
  class TinyModel(TruncatingModel):
    short_field = CharField(max_length=10)
    non_string_field = SmallIntegerField()

  a = TinyModel()

  a.short_field = 'a' * 9 # One less than it's max length
  assert_true(a.short_field == 'a' * 9, 'Short-enough field does not get truncated')

  a.short_field = 'a' * 11 # One more than it's max_length
  assert_true(a.short_field == 'a' * 10, 'Too-long field gets truncated')

  a.non_string_field = 10**10
  assert_true(a.non_string_field == 10**10, 'non-string fields are not truncated')


def test_error_handling():
  raise SkipTest

  restore_django_debug = desktop.conf.DJANGO_DEBUG_MODE.set_for_testing(False)
  restore_500_debug = desktop.conf.HTTP_500_DEBUG_MODE.set_for_testing(False)

  exc_msg = "error_raising_view: Test earráid handling"
  def error_raising_view(request, *args, **kwargs):
    raise Exception(exc_msg)

  def popup_exception_view(request, *args, **kwargs):
    raise PopupException(exc_msg, title="earráid", detail=exc_msg)

  # Add an error view
  error_url_pat = patterns('',
                           url('^500_internal_error$', error_raising_view),
                           url('^popup_exception$', popup_exception_view))
  desktop.urls.urlpatterns.extend(error_url_pat)
  try:
    def store_exc_info(*args, **kwargs):
      pass
    # Disable the test client's exception forwarding
    c = make_logged_in_client()
    c.store_exc_info = store_exc_info

    response = c.get('/500_internal_error')
    assert_true(any(["500.mako" in _template.filename for _template in response.template]))
    assert_true('Thank you for your patience' in response.content)
    assert_true(exc_msg not in response.content)

    # Now test the 500 handler with backtrace
    desktop.conf.HTTP_500_DEBUG_MODE.set_for_testing(True)
    response = c.get('/500_internal_error')
    assert_equal(response.template.name, 'Technical 500 template')
    assert_true(exc_msg in response.content)

    # PopupException
    response = c.get('/popup_exception')
    assert_true(any(["popup_error.mako" in _template.filename for _template in response.template]))
    assert_true(exc_msg in response.content)
  finally:
    # Restore the world
    for i in error_url_pat:
      desktop.urls.urlpatterns.remove(i)
    restore_django_debug()
    restore_500_debug()


def test_app_permissions():
  USERNAME = 'test_app_permissions'
  GROUPNAME = 'impala_only'

  c = make_logged_in_client(USERNAME, groupname=GROUPNAME, recreate=True, is_superuser=False)

  # Reset all perms
  GroupPermission.objects.filter(group__name=GROUPNAME).delete()

  # Access to nothing
  assert_equal(401, c.get('/beeswax', follow=True).status_code)
  assert_equal(401, c.get('/impala', follow=True).status_code)
  assert_equal(401, c.get('/hbase', follow=True).status_code)

  # Add access to beeswax
  grant_access(USERNAME, GROUPNAME, "beeswax")
  assert_equal(200, c.get('/beeswax', follow=True).status_code)
  assert_equal(401, c.get('/impala', follow=True).status_code)
  assert_equal(401, c.get('/hbase', follow=True).status_code)

  # Add access to hbase
  grant_access(USERNAME, GROUPNAME, "hbase")
  assert_equal(200, c.get('/beeswax', follow=True).status_code)
  assert_equal(401, c.get('/impala', follow=True).status_code)
  assert_equal(200, c.get('/hbase', follow=True).status_code)

  # Reset all perms
  GroupPermission.objects.filter(group__name=GROUPNAME).delete()

  assert_equal(401, c.get('/beeswax', follow=True).status_code)
  assert_equal(401, c.get('/impala', follow=True).status_code)
  assert_equal(401, c.get('/hbase', follow=True).status_code)

  # Test only impala perm
  grant_access(USERNAME, GROUPNAME, "impala")
  assert_equal(401, c.get('/beeswax', follow=True).status_code)
  assert_equal(200, c.get('/impala', follow=True).status_code)
  assert_equal(401, c.get('/hbase', follow=True).status_code)


def test_error_handling_failure():
  # Change rewrite_user to call has_hue_permission
  # Try to get filebrowser page
  # test for default 500 page
  # Restore rewrite_user
  import desktop.auth.backend

  c = make_logged_in_client()

  restore_django_debug = desktop.conf.DJANGO_DEBUG_MODE.set_for_testing(False)
  restore_500_debug = desktop.conf.HTTP_500_DEBUG_MODE.set_for_testing(False)

  original_rewrite_user = desktop.auth.backend.rewrite_user

  def rewrite_user(user):
    user = original_rewrite_user(user)
    delattr(user, 'has_hue_permission')
    return user

  original_rewrite_user = desktop.auth.backend.rewrite_user
  desktop.auth.backend.rewrite_user = rewrite_user

  try:
    # Make sure we are showing default 500.html page.
    # See django.test.client#L246
    assert_raises(AttributeError, c.get, reverse('desktop.views.dump_config'))
  finally:
    # Restore the world
    restore_django_debug()
    restore_500_debug()
    desktop.auth.backend.rewrite_user = original_rewrite_user


def test_404_handling():
  view_name = '/the-view-that-is-not-there'
  c = make_logged_in_client()
  response = c.get(view_name)
  assert_true(any(['404.mako' in _template.filename for _template in response.template]), response.template)
  assert_true('Not Found' in response.content)
  assert_true(view_name in response.content)

class RecordingHandler(logging.Handler):
  def __init__(self, *args, **kwargs):
    logging.Handler.__init__(self, *args, **kwargs)
    self.records = []

  def emit(self, r):
    self.records.append(r)

def test_log_event():
  c = make_logged_in_client()
  root = logging.getLogger("desktop.views.log_frontend_event")
  handler = RecordingHandler()
  root.addHandler(handler)

  c.get("/desktop/log_frontend_event?level=info&message=foo")
  assert_equal("INFO", handler.records[-1].levelname)
  assert_equal("Untrusted log event from user test: foo", handler.records[-1].message)
  assert_equal("desktop.views.log_frontend_event", handler.records[-1].name)

  c.get("/desktop/log_frontend_event?level=error&message=foo2")
  assert_equal("ERROR", handler.records[-1].levelname)
  assert_equal("Untrusted log event from user test: foo2", handler.records[-1].message)

  c.get("/desktop/log_frontend_event?message=foo3")
  assert_equal("INFO", handler.records[-1].levelname)
  assert_equal("Untrusted log event from user test: foo3", handler.records[-1].message)

  c.post("/desktop/log_frontend_event", {
    "message": "01234567" * 1024})
  assert_equal("INFO", handler.records[-1].levelname)
  assert_equal("Untrusted log event from user test: " + "01234567"*(1024/8),
    handler.records[-1].message)

  root.removeHandler(handler)

def test_validate_path():
  reset = desktop.conf.SSL_PRIVATE_KEY.set_for_testing('/')
  assert_equal([], validate_path(desktop.conf.SSL_PRIVATE_KEY, is_dir=True))
  reset()

  reset = desktop.conf.SSL_PRIVATE_KEY.set_for_testing('/tmm/does_not_exist')
  assert_not_equal([], validate_path(desktop.conf.SSL_PRIVATE_KEY, is_dir=True))
  reset()

@attr('requires_hadoop')
def test_config_check():
  reset = (
    desktop.conf.SECRET_KEY.set_for_testing(''),
    desktop.conf.SSL_CERTIFICATE.set_for_testing('foobar'),
    desktop.conf.SSL_PRIVATE_KEY.set_for_testing(''),
    desktop.conf.DEFAULT_SITE_ENCODING.set_for_testing('klingon')
  )

  try:
    cli = make_logged_in_client()
    resp = cli.get('/desktop/debug/check_config')
    assert_true('Secret key should be configured' in resp.content, resp)
    assert_true('desktop.ssl_certificate' in resp.content, resp)
    assert_true('Path does not exist' in resp.content, resp)
    assert_true('SSL private key file should be set' in resp.content, resp)
    assert_true('klingon' in resp.content, resp)
    assert_true('Encoding not supported' in resp.content, resp)

    # Set HUE_CONF_DIR and make sure check_config returns appropriate conf
    os.environ["HUE_CONF_DIR"] = "/tmp/test_hue_conf_dir"
    resp = cli.get('/desktop/debug/check_config')
    del os.environ["HUE_CONF_DIR"]
    assert_true('/tmp/test_hue_conf_dir' in resp.content, resp)
  finally:
    for old_conf in reset:
      old_conf()


def test_last_access_time():
  c = make_logged_in_client(username="access_test")
  c.post('/accounts/login/')
  login = desktop.auth.views.get_current_users()
  before_access_time = time.time()
  response = c.get('/home')
  after_access_time = time.time()
  access = desktop.auth.views.get_current_users()

  user = response.context['user']
  login_time = login[user]['time']
  access_time = access[user]['time']

  # Check that 'last_access_time' is later than login time
  assert_true(login_time < access_time)
  # Check that 'last_access_time' is in between the timestamps before and after the last access path
  assert_true(before_access_time < access_time)
  assert_true(access_time < after_access_time)


def test_ui_customizations():
  custom_banner = 'test ui customization'
  reset = (
    desktop.conf.CUSTOM.BANNER_TOP_HTML.set_for_testing(custom_banner),
  )

  try:
    c = make_logged_in_client()
    resp = c.get('/about', follow=True)
    assert_true(custom_banner in resp.content, resp)
  finally:
    for old_conf in reset:
      old_conf()


@attr('requires_hadoop')
def test_check_config_ajax():
  c = make_logged_in_client()
  response = c.get(reverse(check_config))
  assert_true("misconfiguration" in response.content, response.content)


class TestDocModelTags():
  def setUp(self):
    self.client = make_logged_in_client(username="tag_user")
    self.client_not_me = make_logged_in_client(username="not_tag_user")

    self.user = User.objects.get(username="tag_user")
    self.user_not_me = User.objects.get(username="not_tag_user")

    grant_access(self.user.username, self.user.username, "desktop")
    grant_access(self.user_not_me.username, self.user_not_me.username, "desktop")

  def add_tag(self, name):
    response = self.client.post("/desktop/api/tag/add_tag", {'name': name})
    assert_equal(0, json.loads(response.content)['status'], response.content)
    return json.loads(response.content)['tag_id']

  def add_doc(self, name):
    script = PigScript.objects.create(owner=self.user)
    doc = Document.objects.link(script, owner=script.owner, name=name)
    return script, doc

  def test_add_tag(self):
    response = self.client.get("/desktop/api/tag/add_tag")
    assert_equal(-1, json.loads(response.content)['status'])

    tag_id = self.add_tag('my_tag')

    assert_true(DocumentTag.objects.filter(id=tag_id, owner=self.user, tag='my_tag').exists())

  def test_remove_tags(self):
    response = self.client.post("/desktop/api/tag/add_tag", {'name': 'my_tag'})
    tag_id = json.loads(response.content)['tag_id']

    response = self.client.get("/desktop/api/tag/remove_tags")
    assert_equal(-1, json.loads(response.content)['status'])

    response = self.client_not_me.post("/desktop/api/tag/remove_tags", {'data': json.dumps({'tag_ids': [tag_id]})})
    assert_equal(-1, json.loads(response.content)['status'], response.content)

    response = self.client.post("/desktop/api/tag/remove_tags", {'data': json.dumps({'tag_ids': [tag_id]})})
    assert_equal(0, json.loads(response.content)['status'], response.content)

    assert_false(DocumentTag.objects.filter(id=tag_id).exists())

  def test_list_tags(self):
    tag_id = self.add_tag('my_list_tags')

    response = self.client.get("/desktop/api/tag/list_tags")
    assert_true([tag for tag in json.loads(response.content) if tag['id'] == tag_id], response.content)

  def test_list_docs(self):
    script, doc = self.add_doc('test-pig')

    response = self.client.get("/desktop/api/doc/list_docs")
    assert_true([doc for doc in json.loads(response.content) if doc['id'] == script.id], response.content)

  def test_tag(self):
    script, doc = self.add_doc('tag_pig')

    response = self.client.post("/desktop/api/doc/tag", {'data': json.dumps({'doc_id': doc.id, 'tag': 'pig'})})
    assert_equal(0, json.loads(response.content)['status'], response.content)

    tag2_id = self.add_tag('pig2')

    response = self.client.post("/desktop/api/doc/tag", {'data': json.dumps({'doc_id': doc.id, 'tag_id': tag2_id})})
    assert_equal(0, json.loads(response.content)['status'], response.content)

  def test_update_tags(self):
    script, doc = self.add_doc('update_tags')

    tag1_id = self.add_tag('update_tags_1')
    tag2_id = self.add_tag('update_tags_2')

    response = self.client.post("/desktop/api/doc/update_tags", {'data': json.dumps({'doc_id': doc.id, 'tag_ids': [tag1_id, tag2_id]})})
    content = json.loads(response.content)
    
    assert_equal(0, content['status'])
    assert_equal([
        {"id": 1, "name": "default"},
        {"id": 2, "name": "update_tags_1"},
        {"id": 3, "name": "update_tags_2"}
      ], content['doc']['tags'])
    
    # No perms
    response = self.client_not_me.post("/desktop/api/doc/update_tags", {'data': json.dumps({'doc_id': doc.id, 'tag_ids': [tag1_id, tag2_id]})})
    content = json.loads(response.content)
    
    assert_equal(-1, content['status'])
    
    # todo no default tag on test user?



class TestDocModelPermissions():

  def setUp(self):
    self.client = make_logged_in_client(username="perm_user", groupname="default")
    self.client_not_me = make_logged_in_client(username="not_perm_user", groupname="default")

    self.user = User.objects.get(username="perm_user")
    self.user_not_me = User.objects.get(username="not_perm_user")

    grant_access(self.user.username, self.user.username, "desktop")
    grant_access(self.user_not_me.username, self.user_not_me.username, "desktop")
    
    PigScript.objects.filter(owner=self.user).delete()
    Document.objects.filter(owner=self.user).delete()

  def _add_doc(self, name):
    script, created = PigScript.objects.get_or_create(owner=self.user)
    doc = Document.objects.link(script, owner=script.owner, name=name)
    return script, doc

  def test_update_permissions(self):
    script, doc = self._add_doc('test_update_permissions')

    response = self.client.post("/desktop/api/doc/update_permissions", {
        'doc_id': doc.id,
        'data': json.dumps({'read': {'user_ids': [self.user.id, self.user_not_me.id], 'group_ids': []}})
    })

    assert_equal(0, json.loads(response.content)['status'], response.content)

  def test_share_document_permissions(self):
    # No doc
    response = self.client.get('/home')
    assert_equal([], list(response.context['documents']))
    response = self.client_not_me.get('/home')
    assert_equal([], list(response.context['documents']))
        
    # Add doc
    script, doc = self._add_doc('test_update_permissions')

    response = self.client.get('/home')
    assert_equal([doc], list(response.context['documents']))
    response = self.client_not_me.get('/home')
    assert_equal([], list(response.context['documents']))

    # Share by user 
    response = self.client.post("/desktop/api/doc/update_permissions", {
        'doc_id': doc.id,
        'data': json.dumps({'read': {'user_ids': [self.user.id, self.user_not_me.id], 'group_ids': []}})
    })

    assert_equal(0, json.loads(response.content)['status'], response.content)
    
    response = self.client.get('/home')
    assert_equal([doc], list(response.context['documents']))
    response = self.client_not_me.get('/home')
    assert_equal([doc], list(response.context['documents']))

    # Un-share
    response = self.client.post("/desktop/api/doc/update_permissions", {
        'doc_id': doc.id,
        'data': json.dumps({'read': {'user_ids': [self.user.id], 'group_ids': []}})
    })

    assert_equal(0, json.loads(response.content)['status'], response.content)
    
    response = self.client.get('/home')
    assert_equal([doc], list(response.context['documents']))
    response = self.client_not_me.get('/home')
    assert_equal([], list(response.context['documents']))

    # Share by group
    default_group = get_default_user_group()
    
    response = self.client.post("/desktop/api/doc/update_permissions", {
        'doc_id': doc.id,
        'data': json.dumps({'read': {'user_ids': [self.user.id], 'group_ids': [default_group.id]}})
    })

    assert_equal(0, json.loads(response.content)['status'], response.content)
    
    response = self.client.get('/home')
    assert_equal([doc], list(response.context['documents']))
    response = self.client_not_me.get('/home')
    assert_equal([doc], list(response.context['documents']))
