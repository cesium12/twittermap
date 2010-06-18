// for debugging purposes
thingy = null;

onload = function() {
  // set up shell.
  output = document.getElementById('output');
  var shell = new Shell(output);

  // set up stomp client.
  stomp = new STOMPClient();
  stomp.onopen = function() {
    display("Transport opened");
    stomp.subscribe(instream);
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
    if (frame.body.toString().substring(1, 8) === "MESSAGE") {
      return;
    }
    info = JSON.parse(frame.body.toString()).data.vector; // vectornet unprocessing
    viewer.handleMessage(info);
  };
  stomp.connect('localhost', 61613, 'legacy', 'pohgh7Ohf9aeshum');
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


/* The SOMViewer class updates an HTML view to show what is going on in a
 * self-organizing map.
 */

function SOMViewer() {
  if ( !(this instanceof arguments.callee) )
    throw Error("Constructor called as a function");

  this.height = 150;
  this.width = 150;
  this.cellHeight = 0.6;
  this.cellWidth = 0.8;
  this.cellUnit = "em";
  this.cells = {};
  this.container = document.getElementById('themap');
  this.queueIndex = 0;
  this.queueMax = 800;
  this.queue = [];

  this.handleMessage = function(info) {
    var vec = unpack64(info.coordinates);
    var colorvec = this.axisColors(vec);
    this.updateCell(info.text, info.x, info.y, info.width, info.height, colorvec, info.img);
  }
  
  this.makeCell = function() {
    var cell = document.createElement("div");
    cell.setAttribute("class", "cell-off");
    this.container.appendChild(cell);

    var header = document.createElement("div");
    header.setAttribute("class", "header");
    cell.appendChild(header);
    var headerText = document.createTextNode("");
    header.appendChild(headerText);
    var spanTag = document.createElement("span");
    cell.appendChild(spanTag);
    var textNode = document.createTextNode("");
    spanTag.appendChild(textNode);
    var imgTag = document.createElement("img");
    cell.appendChild(imgTag);

    cell.theHeader = header;
    cell.theHeaderText = headerText;
    cell.theSpan = spanTag;
    cell.theText = textNode;
    cell.theImg = imgTag;
    return cell;
  }

  for (var i=0; i<this.queueMax; i++) {
    this.queue[i] = this.makeCell();
  }
  
  this.ageCell = function(cell) {
    cell.setAttribute("class", cell.getAttribute("class").replace(/new/g, "old"));
  }

  this.updateCell = function(text, x, y, width, height, color, img) {
    this.queueIndex = (this.queueIndex + 1) % this.queueMax;
    for (var i=0; i < this.queueMax / 80; i++) {
      this.ageCell(this.queue[(this.queueIndex + i*80) % this.queueMax]);
    }
    var cell = this.queue[this.queueIndex];

    if (this.cells[text]) {
      cell = this.cells[text];
    }
    else if (this.cells[cell.text]) {
      delete this.cells[cell.text];
    }
    if (!cell.setAttribute) {
      delete cell;
      cell = this.queue[this.queueIndex] = this.makeCell();
    }
    cell.setAttribute("class", "off");
    cell.theText.nodeValue = "";
    cell.theHeaderText.nodeValue = "";
    cell.style.left = (x * this.cellWidth) + this.cellUnit;
    cell.style.top = (y * this.cellHeight) + this.cellUnit;
    if (!text || text === "not") {return cell;}
    var type = "concept";
    if (img) {
      cell.theImg.src = img;
      cell.theHeaderText.nodeValue = text;
      cell.theImg.style.width = (width * 0.6 * this.cellWidth) + this.cellUnit;
      cell.theImg.style.height = (height * 0.6 * this.cellWidth) + this.cellUnit;
      type = "user";
    }
    cell.style.color = "rgb("+color[0]+","+color[1]+
      ","+color[2]+")";
    
    if (text.charAt(0) === '@' && text.indexOf(' ') > 0) {
      pos = text.indexOf(' ');
      cell.theHeaderText.nodeValue = text.substring(0, pos);
      text = text.substring(pos + 1);
      type = "tweet";
    }
    
    var fontSize = (height*4) + "pt";
    if (type === "concept") {
      cell.theSpan.style.fontSize = fontSize;
    } else {
      cell.theSpan.style.fontSize = "inherit";
    }
    cell.theText.nodeValue = text;
    var theclass = "cell new "+type;
    if (type === "tweet") theclass += " tweet-new";
    cell.setAttribute("class", theclass);
    this.cells[text] = cell;
    return cell;
  }

  this.axisColors = function(vec) {
    var colorvec = new Array(3);
    for (var i=0; i<3; i++) {
      colorvec[i] = constrain(Math.floor(90 + 1000*(vec[i+1] +
      vec[i+4] + vec[i+7] + vec[i+10] + vec[i+13] + vec[i+16])), 0, 180);
    }
    return colorvec;
  }

  this.mouseWheel = function(notches) {
  }
};

viewer = new SOMViewer();

/* Mouse wheel handling */
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


/** disabled so we can scroll

if (window.addEventListener)
  // Mozilla
  window.addEventListener('DOMMouseScroll', wheel, false);
// IE or Opera
window.onmousewheel = document.onmousewheel = wheel;
*/

// vim:sw=2:ts=2:sts=2:tw=0:
