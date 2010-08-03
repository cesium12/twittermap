map = $("<div></div>").attr("class", "map").appendTo("body");
container = $("<div></div>").attr("class", "back").appendTo("body");
background = $("<img></img>").appendTo(container);
display = $("<div></div>").appendTo(container);

onload = function() {
  stomp = new STOMPClient();
  stomp.onopen           = function()      { stomp.subscribe(channel); };
  stomp.onclose          = function(code)  { alert("onclose: " + code); };
  stomp.onerror          = function(error) { alert("onerror: " + error); };
  stomp.onerrorframe     = function(frame) { alert("onerrorframe: " + frame.body); };
  stomp.onconnectedframe = function()      { container.animate({ opacity: 0.3 }, "slow"); };
  stomp.onmessageframe   = function(frame) {
    if(frame.body.toString().substring(1, 8) !== "MESSAGE")
      viewer.handleMessage(jQuery.parseJSON(frame.body.toString()).data.vector);
  };
  stomp.connect.apply(stomp, stompargs);
};
onunload = function() {
  stomp.reset();
}

function axisColors(vec) {
  var color = [ 0, 0, 0 ];
  for(var i = 0; i < 3; i++) {
    for(var j = i + 1; j < vec.length; j += 3)
      color[i] += vec[j];
    color[i] = Math.min(180, Math.floor(90 + 1000 * color[i]));
  }
  return "rgb(" + color.join() + ")";
}

function makeElement(parent, tag, cls) {
  return $(document.createElement(tag)).attr("class", cls || "").appendTo(parent);
}

function makeCell() {
  var cell = makeElement(map, "div", "cell off");
  cell.theHeaderText = makeElement(cell, "div", "header");
  cell.theText       = makeElement(cell, "span", "text");
  cell.theImg        = makeElement(cell, "img");
  cell.opacity       = 0;
  cell.type          = "concept";
  cell.text          = null;
  
  cell.setOpac = function(opac)     { this.css("opacity", (this.opacity = opac) / opacMax); };
  cell.setImg  = function(src, css) { this.theImg.attr("src", src).css(css); };
  
  cell.doHide = function() {
    if(this.opacity) {
      this.attr("class", "cell off").setOpac(0);
      this.text = null;
    }
  };
  cell.doShow = function(x, y, font, text, color, old) {
    var move = { opacity: 1 }, change = { color: color };
    if(x < 0.5) { move.left   = 100 * x       + "%"; change.right  = ""; this.theText.css("text-align", "left"); }
    else        { move.right  = 100 * (1 - x) + "%"; change.left   = ""; this.theText.css("text-align", "right"); }
    if(y < 0.5) { move.top    = 100 * y       + "%"; change.bottom = ""; this.theText.insertAfter(this.theHeaderText); }
    else        { move.bottom = 100 * (1 - y) + "%"; change.top    = ""; this.theText.appendTo(this); }
    this.stop(true).attr("class", "cell new " + this.type).animate(move, old ? "fast" : 0).css(change);
    this.theText.css("fontSize", font + "pt").html(text);
    this.opacity = opacMax;
  };
  cell.doAge = function() {
    if(this.opacity > 1) {
      if(this.opacity == opacMax)
        this.addClass("old");
      this.setOpac(this.opacity - 1);
    } else
      this.doHide();
  };
  
  cell.css({ left: "50%", top: "50%", right: "50%", bottom: "50%" });
  return cell;
}

function Viewer() {
  this.cellMap = {};
  this.cellList = [];
  this.cellPos = 0;
  
  this.queueStart = this.queueEnd = { data: null, prev: null, next: null };
  this.queueLen = 0;
  
  this.handleMessage = function(info) {
    if(Math.random() * queueMax < this.queueLen)
      return;
    this.queueEnd = this.queueEnd.next = { data: info, prev: this.queueEnd, next: null };
    this.queueLen++;
  }
  
  this.queueStep = function() {
    if(this.queueStart.next == null)
      return;
    var info = this.queueStart.data;
    do {
      this.queueStart = this.queueStart.next;
      this.queueLen--;
    } while(this.queueLen > queueMax);
    this.queueStart.prev = null;
    this.showProgress();
    if(info)
      this.updateCell(info);
  }
  
  this.showProgress = function() {
    display.width(100 * this.queueLen / queueMax + "%");
  }
  
  this.ageCells = function() {
    this.cellPos = (this.cellPos + 1) % cellNum;
    for(var i = this.cellPos % cellStep; i < cellNum; i += cellStep)
      this.cellList[i].doAge();
  }
  
  this.checkCell = function(cell, text, img, width, height) {
    cell.type = "concept";
    cell.text = text;
    
    if(img) {
      cell.type = "user";
      cell.setImg(img, { width: width * 12 + "px", height: height * 12 + "px" });
      cell.theHeaderText.html(text);
    } else
      cell.theHeaderText.html("");
    
    var tIndex = text.indexOf(" // ");
    if(tIndex > -1) {
      cell.type = "tweet";
      text = text.substring(0, tIndex);
    }
    var sIndex = text.indexOf(" ");
    if(text.charAt(0) === "@" && sIndex > -1) {
      cell.type = "tweet";
      cell.theHeaderText.html(text.substring(0, sIndex));
      text = text.substring(sIndex + 1);
    }
    
    return text;
  }
  
  this.updateCell = function(info) {
    var text = info.text;
    
    this.ageCells();
    var cell = this.cellList[this.cellPos];
    if(!text || text === "not")
      return cell.doHide();
    var old = this.cellMap[text], isold = old instanceof jQuery;
    if(isold)
      cell = old;
    else {
      delete this.cellMap[cell.text];
      this.cellMap[text] = cell;
    }
    if(cell.text === null)
      isold = true;
    
    text = this.checkCell(cell, text, info.img, info.width, info.height);
    cell.doShow(info.x / somsize[0], info.y / somsize[1], info.height * 3, text, axisColors(info.coordinates), isold);
  }
};

cellNum = 500;
cellStep = 50;
queueMax = 1000;
opacMax = 5;
viewer = new Viewer();

function logo(url, title) {
  document.title = title;
  display.css("background-image", "url(" + url + ")");
  background.attr("src", url).load(function() {
    container.height(background.height()).width(background.width());
  });
}

function start(url, title) {
  logo(url, title);
  for(var i = 0; i < cellNum; i++)
    viewer.cellList.push(makeCell());
  setInterval("viewer.queueStep()", 0);
}
