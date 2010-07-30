/*
 * This code searches for all the <script type="application/processing" target="canvasid">
 * in your page and loads each script in the target canvas with the proper id.
 * It is useful to smooth the process of adding Processing code in your page and starting
 * the Processing.js engine.
 */

if ( window.addEventListener ) {
	window.addEventListener("load", function() {
		var scripts = document.getElementsByTagName("script");
		
		for ( var i = 0; i < scripts.length; i++ ) {
			if ( scripts[i].type == "application/processing" ) {
				var src = scripts[i].src, canvas = scripts[i].nextSibling;
	
				if ( src && src.indexOf("#") ) {
					canvas = document.getElementById( src.substr( src.indexOf("#") + 1 ) );
				} else {
					while ( canvas && canvas.nodeName.toUpperCase() != "CANVAS" )
						canvas = canvas.nextSibling;
				}

				if ( canvas ) {
					proc = Processing(canvas, scripts[i].text);
				}
			}
		}
	}, false);
}

thingy = null;
NUM_POINTS = 1000;
NUM_TEXTS = 50;
DIMENSIONS = 20;
DECAY = 0.9999;

onload = function() {
  output = document.getElementById('output');

  // set up stomp client.
  stomp = new STOMPClient();
  stomp.onopen = function() {
    display("Transport opened");
    stomp.subscribe(channel);
  };
  stomp.onclose = function(code) {
    display("Transport closed (code: " + code + ")");
  };
  stomp.onerror = function(error) {
    alert("onerror: " + error);
  };
  stomp.onerrorframe = function(frame) {
    alert("onerrorframe: " + frame.body);
  };
  stomp.onconnectedframe = function() {
    display("Connected.");
  };
  stomp.onmessageframe = function(frame) {
    if (frame.body.toString().substring(1, 8) == "MESSAGE") {
      return;
    }
    info = JSON.parse(frame.body.toString()).data.vector;
    viewer.handleMessage(info);
  };
  stomp.connect('localhost', 61613);
};
onunload = function() {
  stomp.reset();
}
display = function(text) {
  document.getElementById('output').innerHTML = text;
}

constrain = function(n, min, max) {
  if (n < min) return min;
  else if (n > max) return max;
  else return n;
}

function StreamingViewer(processing) {

  if ( !(this instanceof arguments.callee) )
    throw Error("Constructor called as a function");

  this.width = 800;
  this.height = 700;
  this.screenLeft = -4;
  this.screenRight = 4;
  this.screenBottom = -4;
  this.screenTop = 4;
  var p = processing;
  var pointer = NUM_POINTS-1;
  var colors = [];
  var mouseDown = false;
  var movePt = [400, 350];

  this.data = [];
  this.axes = [];
  this.texts = [];
  this.textmap = {};

  for (var i=0; i<NUM_POINTS; i++) {
    this.data[i] = new Array(DIMENSIONS);
    colors[i] = new Array(3);
  }
  for (var j=0; j<DIMENSIONS; j++) {
    this.axes[j] = [0, 1];
  }

  this.screenX = function(x) {
    return (x-this.screenLeft) / (this.screenRight-this.screenLeft) * this.width;
  }

  this.screenY = function(y) {
    return (y-this.screenTop) / (this.screenBottom-this.screenTop) * this.height;
  }

  this.unscreenX = function(x) {
    return this.screenLeft + (x/this.width) * (this.screenRight-this.screenLeft);
  }

  this.unscreenY = function(y) {
    return this.screenTop + (y/this.height) * (this.screenBottom-this.screenTop);
  }

  this.project = function(vec) {
    var x=0;
    var y=0;
    var norm1 = 0;
    for (var j=2; j<DIMENSIONS; j++) {
      x += this.axes[j][0]*vec[j];
      y += this.axes[j][1]*vec[j];
      norm1 += vec[j]*vec[j];
    }
    norm1 = Math.sqrt(norm1);
    var norm2 = Math.sqrt(x*x+y*y);
    return [x/norm1/norm2, y/norm1/norm2];
  }

  this.truncate = function(text) {
    if (text.length <= 80) return text;
    else {
      return text.substring(0, 80) + '...';
    }
  }

  this.handleMessage = function(info) {
    thingy = info;
    if (info.text.charAt(0) == "(") return;
    vec = info.coordinates;
    this.handleVector(vec, this.truncate(info.text));
    this.handleConcepts(info.concepts);
    p.fill(255);
    this.setMagnitudes(info.magnitudes);
  }

  this.handleConcepts = function(concepts) {
    for (concept in concepts) {
      var vec = concepts[concept];
      for (var i=0; i<vec.length; i++) {
        vec[i] *= 1000;
      }
      this.handleVector(vec, concept);
    }
  }

  this.handleVector = function(vec, text) {
    pointer++;
    pointer %= NUM_POINTS;
    this.texts[pointer] = text;
    this.data[pointer] = vec;
    colors[pointer] = this.axisColors(vec);
  }

  this.setMagnitudes = function(vec) {
    var biggest = vec[1];
    var anglefactor = 30 + 0.2*Math.sin(2*Math.PI*pointer/NUM_POINTS);
    for (var i=1; i<vec.length; i++) {
      var sqrtmag = Math.sqrt(vec[i]/biggest);
      var angle = anglefactor*Math.PI*sqrtmag;
      this.axes[i] = [Math.cos(angle)*sqrtmag, Math.sin(angle)*sqrtmag];
    }
  }

  this.mousePressed = function() {
    if (!mouseDown) {
      mouseDown = true;
      movePt = [this.unscreenX(p.mouseX), this.unscreenY(p.mouseY)];
    }
  }

  this.mouseReleased = function() {
    mouseDown = false;
  }

  this.mouseWheel = function(notches) {
    var mx = this.unscreenX(p.mouseX);
    var my = this.unscreenY(p.mouseY);
    this.zoom(mx, my, notches/10);
  }

  this.zoom = function(x, y, increment) {
    this.screenLeft += (x-this.screenLeft) * increment;
    this.screenRight += (x-this.screenRight) * increment;
    this.screenTop += (y-this.screenTop) * increment;
    this.screenBottom += (y-this.screenBottom) * increment;
  }

  this.decayPoints = function() {
    for (var i=0; i<NUM_POINTS; i++) {
      for (var j=0; j<DIMENSIONS; j++) {
        this.data[i][j] *= DECAY;
      }
    }
  }

  this.updateFollowingMouse = function() {
    if (mouseDown) {
      var deltaX = movePt[0] - this.unscreenX(p.mouseX);
      var deltaY = movePt[1] - this.unscreenY(p.mouseY);
      this.screenLeft += deltaX;
      this.screenRight += deltaX;
      this.screenTop += deltaY;
      this.screenBottom += deltaY;
    }
    display([this.screenLeft, this.screenRight, this.screenTop, this.screenBottom].toString());
  }

  this.draw = function() {
    p.background(50);
    // draw axes
    p.stroke(60, 80, 60);
    for (var j=1; j<DIMENSIONS; j++) {
      p.line(this.screenX(0), this.screenY(0),
             this.screenX(this.axes[j][0]), this.screenY(this.axes[j][1]));
    }
    p.noStroke();

    // draw points
    this.decayPoints();
    this.updateFollowingMouse();
    p.fill(50, 200, 250);
    for (var i=0; i<NUM_POINTS; i++) {
      if (this.texts[i] == undefined) continue;
      //if (this.texts[i].substring(0, 1) == "(") continue;
      proj = this.project(this.data[i]);
      p.fill(colors[i][0], colors[i][1], colors[i][2]);
      p.ellipse(this.screenX(proj[0]), 
                this.screenY(proj[1]), 2, 2);
      if (pointer - i >= 0 && pointer - i < NUM_TEXTS) {
        p.text(this.texts[i], this.screenX(proj[0])+5,
                              this.screenY(proj[1])+5);
      }
    }
  }
};

canvas = document.getElementById("canvas");
p = Processing(canvas);
viewer = new StreamingViewer(p);

p.setup = function() {
  this.size(800, 700);
  this.background(50);
  this.smooth();
  this.ellipseMode(p.CENTER_RADIUS);
  this.noStroke();
}

p.draw = function() {viewer.draw();}
p.mousePressed = function() {viewer.mousePressed();}
p.mouseReleased = function() {viewer.mouseReleased();}

p.init();

/* Ugly mouse wheel handling code from adomas.org/javascript-mouse-wheel/ */
wheel = function(event) {
  if (!event) event = window.event; // IE
  if (event.wheelDelta) { // IE/Opera
    delta = event.wheelDelta/120;
    if (window.opera) delta = -delta;
  } else if (event.detail) { // Mozilla
    delta = -event.detail/3;
  }
  viewer.mouseWheel(delta);
  if (event.preventDefault) event.preventDefault();
  event.returnValue = false;
}
if (window.addEventListener)
  // Mozilla
  window.addEventListener('DOMMouseScroll', wheel, false);
// IE or Opera
window.onmousewheel = document.onmousewheel = wheel;
