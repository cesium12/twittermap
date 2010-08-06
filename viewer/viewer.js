$("body").css({ margin: 0, lineHeight: 0 });
canvas = $("<canvas></canvas>").attr("class", "map").appendTo("body")[0];
context = canvas.getContext("2d");
$(window).resize(function() {
  canvas.height = $(window).height();
  canvas.width  = $(window).width();
}).resize();

onload = function() {
  stomp = new STOMPClient();
  stomp.onopen           = function()      { stomp.subscribe(channel); };
  stomp.onclose          = function(code)  { alert("onclose: " + code); };
  stomp.onerror          = function(error) { alert("onerror: " + error); };
  stomp.onerrorframe     = function(frame) { alert("onerrorframe: " + frame.body); };
  stomp.onconnectedframe = function()      { $(canvas).animate({ opacity: 1 }, "slow") };
  stomp.onmessageframe   = function(frame) { viewer.handleMessage(jQuery.parseJSON(frame.body.toString())); };
  stomp.connect("localhost", 61613);
};
onunload = function() {
  stomp.reset();
};

function StreamingViewer() {
  this.screenLeft = -4;
  this.screenTop = 4;
  this.screenWidth = 8;
  this.screenHeight = -8;
  
  this.numPoints = 1000;
  this.numTexts = 50;
  this.numDims = 20;
  this.decay = 0.9999;
  
  this.pointer = 0;
  this.mousePt = null;
  this.items = [];
  this.axes = [];
  
  var self = this;
  $(canvas).mousedown (function(e)    { self.mousePt = self.mouseXY(e);     })
           .mouseup   (function()     { self.mousePt = null;                })
           .mousewheel(function(e, d) { self.zoom(self.mouseXY(e), d / 10); })
           .mousemove (function(e)    { self.pan(self.mouseXY(e));          });
  $(window).resize    (function()     { self.draw();                        });
  
  for(var i = 0; i < this.numPoints; i++)
    this.items.push({ data: new Array(this.numDims), color: [0, 0, 0], text: "" });
  for(var i = 0; i < this.numDims; i++)
    this.axes[i] = [0, 1];

  this.screenX = function(x) { return (x - this.screenLeft) / this.screenWidth  * canvas.width;  };
  this.screenY = function(y) { return (y - this.screenTop ) / this.screenHeight * canvas.height; };
  this.mouseXY = function(e) { return [ this.screenLeft + e.pageX * this.screenWidth  / canvas.width,
                                        this.screenTop  + e.pageY * this.screenHeight / canvas.height ]; };

  this.project = function(vec) {
    var x = 0, y = 0, norm1 = 0;
    for(var j = 2; j < this.numDims; j++) {
      x += this.axes[j][0] * vec[j];
      y += this.axes[j][1] * vec[j];
      norm1 += vec[j] * vec[j];
    }
    norm1 = Math.sqrt(norm1);
    var norm2 = Math.sqrt(x * x + y * y);
    return [ x / norm1 / norm2, y / norm1 / norm2 ];
  };

  this.handleMessage = function(info) {
    if(info.text.length > 20)
      info.text = info.text.substring(0, 17) + "...";
    if(info.text.charAt(0) != "(") {
      this.handleVector(info.coordinates, info.text);
      this.handleConcepts(info.concepts);
      this.handleMagnitudes(info.magnitudes);
      this.draw();
    }
  };
  this.handleConcepts = function(concepts) {
    for(concept in concepts)
      this.handleVector(concepts[concept].map(function(x) { return x * 1000; }), concept);
  };
  this.handleVector = function(vec, text) {
    this.items[this.pointer] = { data: vec, color: this.axisColors(vec).map(function(x) { return parseInt(x); }), text: text };
    this.pointer = (this.pointer + 1) % this.numPoints;
  };
  this.handleMagnitudes = function(vec) {
    var sqrtmag, angle;
    var anglefactor = 30 + 0.2 * Math.sin(2 * Math.PI * this.pointer / this.numPoints);
    for(var i = 1; i < vec.length; i++) {
      sqrtmag = Math.sqrt(vec[i] / vec[1]);
      angle = anglefactor * Math.PI * sqrtmag;
      this.axes[i] = [ Math.cos(angle) * sqrtmag, Math.sin(angle) * sqrtmag ];
    }
  };
  
  this.zoom = function(point, increment) {
    this.screenLeft   += (point[0] - this.screenLeft) * increment;
    this.screenTop    += (point[1] - this.screenTop ) * increment;
    this.screenWidth  *= 1 - increment;
    this.screenHeight *= 1 - increment;
    this.draw();
  };
  this.pan = function(point) {
    if(this.mousePt) {
      this.screenLeft += this.mousePt[0] - point[0];
      this.screenTop  += this.mousePt[1] - point[1];
      this.draw();
    }
  };
  
  this.drawBack = function(color) {
    context.fillRect(0, 0, canvas.width, canvas.height);
  };
  this.drawLine = function(p1, p2) {
    context.beginPath();
    context.moveTo(this.screenX(p1[0]), this.screenY(p1[1]));
    context.lineTo(this.screenX(p2[0]), this.screenY(p2[1]));
    context.stroke();
    context.closePath();
  };
  this.drawCirc = function(p, r) {
    context.beginPath();
    context.arc(this.screenX(p[0]), this.screenY(p[1]), r, 0, 2 * Math.PI, false);
    context.fill();
    context.closePath();
  };
  this.drawText = function(text, p, off) {
    context.fillText(text, this.screenX(p[0]) + off, this.screenY(p[1]) + off);
  };
  
  this.draw = function() {
    context.fillStyle = "rgb(50,50,50)";
    this.drawBack();
    context.strokeStyle = "rgb(60,80,60)";
    for(var i = 1; i < this.numDims; i++)
      this.drawLine([0, 0], this.axes[i]);
    for(var i = 0; i < this.numPoints; i++) {
      var item = this.items[i];
      if(item.text) {
        proj = this.project(item.data);
        context.fillStyle = "rgb(" + item.color.join() + ")";
        this.drawCirc(proj, 2);
        if((i + this.numTexts) % this.numPoints > this.pointer && i <= this.pointer)
          this.drawText(item.text, proj, 5);
      }
    }
  };
};

viewer = new StreamingViewer();
