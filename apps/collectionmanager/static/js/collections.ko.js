// Licensed to Cloudera, Inc. under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  Cloudera, Inc. licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Start Models

var Collection = function(viewModel) {
  var self = this;

  self.name = ko.observable().extend({'errors': null});
  self.fields = ko.observableArray();

  self.removeField = function(field) {
    self.fields.remove(field);
  };

  self.addField = function(name, type) {
    self.fields.push(new Field(self, name, type));
  };

  self.newField = function() {
    self.addField('', '');
  };

  self.setData = function(data_json) {
    self.data(data_json);
  };
};

var Field = function(collection, name, type) {
  var self = this;

  self.name = ko.observable(name).extend({'errors': null});
  self.type = ko.observable(type).extend({'errors': null});

  self.remove = function() {
    collection.removeField(self);
  };
};

// End Models


// Start Wizard

var Page = function(url, name, next, validate_fn) {
  var self = this;

  self.name = ko.observable(name);
  self.url = ko.observable(url);
  self.next = ko.observable(next);

  self.validate = validate_fn || function() { return true; };
};

var Wizard = function() {
  var self = this;

  self.rootPage = ko.observable();
  self.currentPage = ko.observable(self.rootPage());
  // Stack of previous pages.
  self.previousPages = ko.observableArray();

  self.hasPrevious = ko.computed(function() {
    return self.previousPages().length > 0;
  });

  self.hasNext = ko.computed(function() {
    return !!(self.currentPage() && self.currentPage().next());
  });

  self.pageList = ko.computed(function() {
    var page = self.rootPage();
    var pages = [];
    while(page) {
      pages.push(page);
      page = self.pages[page.next()];
    }
    return pages;
  });

  self.previousUrl = ko.computed(function() {
    if (self.previousPages().length > 0) {
      return self.previousPages()[self.previousPages().length - 1].url();
    } else {
      return null;
    }
  });

  self.nextUrl = ko.computed(function() {
    if (self.currentPage() && self.currentPage().next()) {
      return self.currentPage().next();
    } else {
      return null;
    }
  });

  self.next = function() {
    if (self.hasNext() && self.currentPage().validate()) {
      self.previousPages.push(self.currentPage());
      self.currentPage(self.pages[self.currentPage().next()]);
    }
  };

  self.previous = function() {
    if (self.hasPrevious()) {
      self.currentPage(self.previousPages.pop());
    }
  };

  self.setPageByUrl = function(url) {
    var urls = ko.utils.arrayMap(self.pageList(), function(page) {
      return page.url();
    });
    var previousUrls = ko.utils.arrayMap(self.previousPages(), function(page) {
      return page.url();
    });
    if ($.inArray(url, previousUrls) != -1) {
      var previousPageURL = null;
      self.previous();
      while(self.hasPrevious() && self.currentPage().url() != url && self.currentPage().url() != previousPageURL) {
        previousPageURL = self.currentPage().url();
        self.previous();
      }
    } else if ($.inArray(url, urls) != -1) {
      var previousPageURL = null;
      while(self.hasNext() && self.currentPage().url() != url && self.currentPage().url() != previousPageURL) {
        previousPageURL = self.currentPage().url();
        self.next();
      }
    }
  };
};

ko.utils.extend(Wizard.prototype, {
  'pages': {},
  'getPage': function(url, name, next, validate_fn) {
    if (!this.pages[url]) {
      this.pages[url] = new Page(url, name, next, validate_fn);
    }
    return this.pages[url];
  }
});

// End Wizard

var CreateCollectionViewModel = function(wizard) {
  var self = this;

  var fieldTypes = [
    'string',
    'integer',
    'float',
    'boolean'
  ];
  var fieldSeparators = [
    ',',
    '\t'
  ];
  var dataTypes = [
    // 'log',
    // 'regex',
    'separated'
  ];

  // Models
  self.fieldTypes = ko.mapping.fromJS(fieldTypes);
  self.fieldSeparators = ko.mapping.fromJS(fieldSeparators);
  self.dataTypes = ko.mapping.fromJS(dataTypes);
  self.collection = new Collection(self);
  self.dataType = ko.observable().extend({'errors': null});
  self.fieldSeparator = ko.observable().extend({'errors': null});

  // UI
  self.wizard = wizard;

  self.inferFields = function(data) {
    var fields = [];
    var field_names = data[0];
    var first_row = data[1];
    $.each(first_row, function(index, value) {
      var type = null;
      if ($.isNumeric(value)) {
        if (value.toString().indexOf(".") == -1) {
          type = 'integer';
        } else {
          type = 'float';
        }
      } else {
        if (value.toLowerCase().indexOf("true") > -1 || value.toLowerCase().indexOf("false") > -1) {
          type = 'boolean';
        }
        else {
          type = 'string';
        }
      }
      fields.push(new Field(self.collection, field_names[index], type));
    });

    self.collection.fields(fields);
  };

  self.save = function() {
    if (self.wizard.currentPage().validate()) {
      return $.post("/collectionmanager/api/create/", {
        collection: ko.toJSON(self.collection),
      })
      .done(function(data) {
        if (data.status == 0) {
          window.location.href = '/collectionmanager';
        } else {
          $(document).trigger("error", data.message);
        }
      })
      .fail(function (xhr, textStatus, errorThrown) {
        $(document).trigger("error", xhr.responseText);
      });
    }
  };
};


var ImportCollectionViewModel = function(steps) {
  var self = this;

  self.collections = ko.observableArray();
  self.cores = ko.observableArray();

  self.importable = ko.computed(function() {
    return self.collections().concat(self.cores());
  });

  self.selectedImportable = ko.computed(function() {
    return ko.utils.arrayFilter(self.importable(), function(collection_or_core) {
      return collection_or_core.selected();
    });
  });

  self.loadCollectionsAndCores = function() {
    return $.get("/collectionmanager/api/collections_and_cores/")
    .done(function(data) {
      if (data.status == 0) {
        self.collections(ko.utils.arrayMap(data.collections, function(collection) {
          collection = ko.mapping.fromJS(collection);
          collection.selected = ko.observable(false);
          return collection;
        }));
        self.cores(ko.utils.arrayMap(ko.mapping.fromJS(data.cores)(), function(core) {
          core = ko.mapping.fromJS(core);
          core.selected = ko.observable(false);
          return core;
        }));
      } else {
        $(document).trigger("error", data.message);
      }
    })
    .fail(function (xhr, textStatus, errorThrown) {
      $(document).trigger("error", xhr.responseText);
    });
  };

  self.importSelected = function() {
    return $.post("/collectionmanager/api/import/", {
      collections: ko.mapping.toJSON(self.selectedImportable()),
    })
    .done(function(data) {
      if (data.status == 0) {
        window.location.href = '/collectionmanager';
      } else {
        $(document).trigger("error", data.message);
      }
    })
    .fail(function (xhr, textStatus, errorThrown) {
      $(document).trigger("error", xhr.responseText);
    });
  };
};


// Start utils

ko.bindingHandlers.routie = {
  init: function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
    $(element).click(function() {
      var obj = ko.utils.unwrapObservable(valueAccessor());
      var url = null;
      var bubble = false;
      if ($.isPlainObject(obj)) {
        url = obj.url;
        bubble = !!obj.bubble;
      } else {
        url = obj;
      }
      routie(url);
      return bubble;
    });
  }
};

ko.extenders.errors = function(target, options) {
  target.errors = ko.observableArray();
  return target;
};

qq.CollectionFileUploader = function(o){
  // call parent constructor
  qq.FileUploader.apply(this, arguments);

  this._handler._upload = function(id, params){
    var file = this._files[id],
        name = this.getName(id),
        size = this.getSize(id);

    this._loaded[id] = 0;

    var xhr = this._xhrs[id] = new XMLHttpRequest();
    var self = this;

    xhr.upload.onprogress = function(e){
      if (e.lengthComputable){
        self._loaded[id] = e.loaded;
        self._options.onProgress(id, name, e.loaded, e.total);
      }
    };

    xhr.onreadystatechange = function(){
      if (xhr.readyState == 4){
        self._onComplete(id, xhr);
      }
    };

    var formData = new FormData();
    formData.append(params.fileFieldLabel, file);
    formData.append('field-separator', params.fieldSeparator);

    var action = this._options.action;
    xhr.open("POST", action, true);
    xhr.send(formData);
  };
};

qq.extend(qq.CollectionFileUploader.prototype, qq.FileUploader.prototype);

qq.extend(qq.CollectionFileUploader.prototype, {
  _finish: [],
  _onInputChange: function(input){
    if (this._handler instanceof qq.UploadHandlerXhr) {
      this._finish.push(this._uploadFileList.bind(this, input.files));
    } else {
      if (this._validateFile(input)) {
        this._finish.push(this._uploadFile.bind(this, input));
      }
    }
    this._button.reset();
  },
  finishUpload: function() {
    $.each(this._finish, function(index, upload) {
      upload();
    });
  }
});

// End utils
