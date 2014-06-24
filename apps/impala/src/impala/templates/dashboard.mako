## Licensed to Cloudera, Inc. under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  Cloudera, Inc. licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
<%!
  from desktop.views import commonheader, commonfooter
  from django.utils.translation import ugettext as _
%>

<%namespace name="actionbar" file="actionbar.mako" />

${ commonheader(None, "impala", user) | n,unicode }

<div class="container-fluid">
  <div class="row-fluid">
    <div class="span12">
      <div class="card card-home">
        <input type="text" data-bind="spinedit: randomNumber" />

        <br/>
        The random number is <span data-bind="text: randomNumber"></span>
        <br/>

        <div style="width: 300px; height: 300px">
          <div data-bind="pieChart: {data: olives,
        transformer: pieChartDataTransformer,
        maxWidth: 250,
        onClick: function(d){ alert('The olive ' + d.data.obj.name() + ' comes from ' + d.data.obj.country()) },
        onComplete: function(){ console.log('complete') }}"></div>
        </div>

        <br/>
        <br/>
      </div>
    </div>
  </div>
</div>

<script src="/static/ext/js/knockout-min.js" type="text/javascript" charset="utf-8"></script>
<script src="/static/ext/js/knockout.mapping-2.3.2.js" type="text/javascript" charset="utf-8"></script>

<%namespace name="dashboard" file="common_dashboard.mako" />

${ dashboard.import_bindings() }
${ dashboard.import_charts() }

<script type="text/javascript">
  function pieChartDataTransformer(data){
    var _data = [];
    $(data()).each(function (cnt, item) {
      _data.push({
        label: item.name(),
        value: item.acidity(),
        obj: item
      });
    });
    return _data;
  }

  var Olive = function(name, country, acidity){
    var self = this;
    self.name = ko.observable(name);
    self.country = ko.observable(country);
    self.acidity = ko.observable(acidity);
  }

  var TestViewModel = function () {
    var self = this;
    self.randomNumber = ko.observable(12);
    self.olives = ko.observableArray([
      new Olive("kalamata", "greece", 5),
      new Olive("taggiasca", "italy", 9)
    ]);
  };

  var viewModel = new TestViewModel();
  ko.applyBindings(viewModel);
</script>

${ commonfooter(messages) | n,unicode }
