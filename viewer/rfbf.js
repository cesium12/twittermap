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
    stomp.subscribe("/topic/SocNOC/redfishbluefish");
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
    display("");
  };
  stomp.onmessageframe = function(frame) {
    if (frame.body.toString().substring(1, 8) === "MESSAGE") {
      return;
    }
    info = JSON.parse(frame.body.toString());
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

similarity = function(vec1, vec2) {
  var total = 0.0;
  var sq_vec1 = 0.0;
  var sq_vec2 = 0.0;
  // yes, skip index 0
  for (var i=1; i<vec1.length; i++) {
    sq_vec1 += vec1[i] * vec1[i];
    sq_vec2 += vec2[i] * vec2[i];
    total += vec1[i] * vec2[i];
  }
  return total / Math.sqrt(sq_vec1) / Math.sqrt(sq_vec2);
}

magnitude = function(vec) {
  var sq = 0.0;
  for (var i=1; i<vec.length; i++) {
    sq += vec[i] * vec[i];
  }
  return Math.sqrt(sq);
}

orthogonalize = function(vec1, vec2) {
  var vecout = new Array(vec1.length);
  var sq_vec1 = 0.0;
  var sq_vec2 = 0.0;
  var total = 0.0;
  for (var i=1; i<vec1.length; i++) {
    sq_vec1 += vec1[i] * vec1[i];
    sq_vec2 += vec2[i] * vec2[i];
    total += vec1[i] * vec2[i];
  }
  for (var i=1; i<vec1.length; i++) {
    vecout[i] = vec2[i] - vec1[i] / sq_vec1 * total;
  }
  return vecout;
}

/* The CategoryViewer class updates an HTML view to show what is going on in a
 * self-organizing map.
 */

function CategoryViewer() {
  if ( !(this instanceof arguments.callee) )
    throw Error("Constructor called as a function");

  this.height = 150;
  this.width = 150;
  this.cellHeight = 0.5;
  this.cellWidth = 0.8;
  this.cellUnit = "em";
  this.cells = {};
  this.container = document.getElementById('themap');
  this.queueIndex = 0;
  this.queueMax = 800;
  this.queue = [];
  this.politics_vec = null;
  this.affect_vec = null;

  this.handleMessage = function(info) {
    if (info.text === undefined) return;
    if (info.text === "") return;
    if (info.text.charAt(0) == '(') return;
    this.person_vec = unpack64(info.categories.person);
    this.politics_vec = orthogonalize(this.person_vec, unpack64(info.categories.politics));
    this.affect_vec = orthogonalize(this.politics_vec, unpack64(info.categories.affect));
    for (var concept in info.concepts) {
      if (concept === "empty") continue;
      var vec = unpack64(info.concepts[concept]);
      var x = similarity(this.politics_vec, vec);
      var y = similarity(this.affect_vec, vec);
      var colorvec = this.catColors(x,y);
      var xp = (x+1)*50;
      var yp = (-y+1)*40;
      size = Math.sqrt(Math.sqrt(magnitude(vec))) * 50;
      this.updateCell(concept, xp, yp, size*2, size/2, colorvec, info.text);
    }
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
    var spanTag2 = document.createElement("span");
    spanTag2.setAttribute("class", "collapse dem");
    cell.appendChild(spanTag2);
    var spanTag3 = document.createElement("span");
    spanTag3.setAttribute("class", "collapse rep");
    cell.appendChild(spanTag3);
    var subtextNodeD = document.createTextNode("");
    spanTag2.appendChild(subtextNodeD);
    var subtextNodeR = document.createTextNode("");
    spanTag3.appendChild(subtextNodeR);
    var imgTag = document.createElement("img");
    cell.appendChild(imgTag);

    cell.theHeader = header;
    cell.theHeaderText = headerText;
    cell.theSpan = spanTag;
    cell.theSpan2 = spanTag2;
    cell.theSpan3 = spanTag3;
    cell.theText = textNode;
    cell.theSubtextD = subtextNodeD;
    cell.theSubtextR = subtextNodeR;
    cell.theImg = imgTag;
    return cell;
  }

  for (var i=0; i<this.queueMax; i++) {
    this.queue[i] = this.makeCell();
  }
  
  this.ageCell = function(cell) {
    cell.setAttribute("class", cell.getAttribute("class").replace(/new/g, "old"));
  }

  this.updateCell = function(text, x, y, width, height, color, subtext) {
    this.queueIndex = (this.queueIndex + 1) % this.queueMax;
    var img=null;
    for (var i=0; i < this.queueMax / 100; i++) {
      this.ageCell(this.queue[(this.queueIndex + i*100) % this.queueMax]);
    }
    var cell = this.queue[this.queueIndex];
    var erase = true;
    if (this.cells[text]) {
      cell = this.cells[text];
      erase = false;
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
    if (erase) {
      cell.theSubtextD.nodeValue = "";
      cell.theSubtextR.nodeValue = "";
    }
    cell.style.left = (x * this.cellWidth) + this.cellUnit;
    cell.style.top = (y * this.cellHeight) + this.cellUnit;
    if (!text || text === "not") {return cell;}
    var type = "concept";
    if (text === "#democrat") {
      img = "donkey.jpg";
      width = 8;
      height = 8;
    }
    if (text === "#republican") {
      img = "elephant.jpg";
      width = 8;
      height = 8;
    }
    if (text.indexOf(' // ') > -1) {
      type = "tweet";
      if (text.indexOf(' #democrat') > -1) {
        color = [0, 0, 255];
      }
      else if (text.indexOf(' #republican') > -1) {
        color = [255, 0, 0];
      }
      text = text.substring(0, text.indexOf(' // '));
      cell.theHeaderText.nodeValue = '';
    }
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
      var subtext2 = subtext.substring(0, subtext.indexOf(' // '));
      if (subtext.indexOf(' #democrat') > 0) {
        cell.theSubtextD.nodeValue = "(D) " + subtext2;
      } else if (subtext.indexOf(' #republican') > 0) {
        cell.theSubtextR.nodeValue = "(R) " + subtext2;
      }
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

  this.catColors = function(x, y) {
    return [Math.floor(80 + 80*x), Math.floor(80 + 40*y), Math.floor(80 - 80*x)];
  }

  this.mouseWheel = function(notches) {
  }
};

viewer = new CategoryViewer();

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
