var display = $("#output");
var container = $("#themap");
var stomp;

onload = function() {
  stomp = new STOMPClient();
  stomp.onopen           = function()      { stomp.subscribe(instream); };
  stomp.onclose          = function(code)  { alert("onclose: " + code); };
  stomp.onerror          = function(error) { alert("onerror: " + error); };
  stomp.onerrorframe     = function(frame) { alert("onerrorframe: " + frame.body); };
  stomp.onconnectedframe = function()      { display.text("Connected."); };
  stomp.onmessageframe   = function(frame) {
    if(frame.body.toString().substring(1, 8) !== "MESSAGE")
      viewer.handleMessage(jQuery.parseJSON(frame.body.toString()).data.vector); // vectornet unprocessing
  };
  stomp.connect.apply(stomp, stompargs);
};
onunload = function() {
  stomp.reset();
}

function makeElement(parent, tag, cls) {
  if(tag) {
    elt = document.createElement(tag);
    elt.setAttribute("class", cls || "");
  } else
    elt = document.createTextNode("");
  parent.append(elt);
  return $(elt);
}

function catColors(x, y) {
  return [Math.floor(80 + 80 * x), Math.floor(80 + 40 * y), Math.floor(80 - 80 * x)];
}

function makeColor(rgb) {
  return "rgb(" + rgb.join() + ")";
}

function makeCell() {
  var cell = makeElement(container, "div", "off cell");
  cell.theHeaderText = makeElement(cell, "div", "header");
  cell.theText       = makeElement(cell, "span", "text");
  cell.theSubtextD   = makeElement(cell, "span", "collapse dem");
  cell.theSubtextR   = makeElement(cell, "span", "collapse rep");
  cell.theSubtext    = $("span.collapse", cell);
  cell.theImg        = makeElement(cell, "img");
  cell.shown         = false;
  
  cell.doAge   = function()           { this.addClass("old").doFade("theText"); };
  cell.doHide  = function()           { this.addClass("off"); this.shown = false; };
  cell.doShow  = function()           { this.attr("class", "cell new " + this.type); this.shown = true; };
  cell.setImg  = function(src, style) { this.theImg.attr("src", src).css(style); }
  cell.setType = function(type)       { this.type = type; return this; }
  
  cell.doFade = function(elt) {
    var child = this[elt];
    var opacity = child.css("opacity") - 0.2;
    if(opacity <= 0) {
        this.doHide();
        opacity = 1;
    }
    child.css("opacity", opacity);
  }
  return cell;
}

function CategoryViewer() {
  if ( !(this instanceof arguments.callee) )
    throw Error("Constructor called as a function");
  
  this.cellMap = {};
  this.cellList = [];
  this.cellNum = 500;
  this.cellStep = 50;
  this.cellPos = 0;
  
  this.queueStart = this.queueEnd = { data: null, prev: null, next: null };
  this.queueMax = 1000;
  this.queueLen = 0;
  this.queueDrop = 0.8;
  
  for(i = 0; i < this.cellNum; i++)
    this.cellList.push(makeCell());
  
  this.handleMessage = function(info) {
    if(Math.random() < this.queueDrop)
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
    } while(this.queueLen > this.queueMax);
    this.queueStart.prev = null;
    display.text(this.queueLen);
    if(info)
      this.updateCell(info.concept, info.text,
                      1 + info.x, 1 - info.y,
                      info.size * 100, info.size * 25,
                      catColors(info.x, info.y));
  };
  
  this.updateCell = function(text, subtext, x, y, width, height, color) {
    this.cellPos = (this.cellPos + 1) % this.cellNum;
    for(i = this.cellPos % this.cellStep; i < this.cellNum; i += this.cellStep)
      if(this.cellList[i].shown)
        this.cellList[i].doAge();
    
    var cell = this.cellList[this.cellPos];
    if(typeof(this.cellMap[text]) === "object")
      cell = this.cellMap[text];
    else
      cell.theSubtext.text("");
    if(!text || text === "not")
      return cell.doHide();
    cell.setType("concept").theHeaderText.text("");
    this.cellMap[text] = cell;
    
    var imgDim = "3.84em";
    if(text === "#democrat")
      cell.setType("user").setImg("donkey.png", { width : "3.84em" });
    if(text === "#republican")
      cell.setType("user").setImg("elephant.png", { width : "3.84em" });
    
    var tIndex = text.indexOf(" // "), sIndex = text.indexOf(" ");
    if(tIndex > -1) {
      if(text.indexOf(" #democrat") > -1)
        color = [0, 0, 255];
      else if(text.indexOf(" #republican") > -1)
        color = [255, 0, 0];
      cell.setType("tweet");
      text = text.substring(0, tIndex);
    }
    if(text.charAt(0) === "@" && sIndex > 0) {
      cell.setType("tweet");
      cell.theHeaderText.text(text.substring(0, sIndex));
      text = text.substring(sIndex + 1);
    }
    
    if(cell.type === "concept") {
      var subtext2 = subtext.split(" // ", 1)[0];
      if(subtext.indexOf(" #democrat") > 0)
        cell.theSubtextD.text("(D) " + subtext2);
      if(subtext.indexOf(" #republican") > 0)
        cell.theSubtextR.text("(R) " + subtext2);
    }
    cell.theText.css("fontSize", height * 4 + "pt").text(text);
    cell.css({ left  : x * 40 + "em",
               top   : y * 20 + "em",
               color : makeColor(color) }).doShow();
  };
}

viewer = new CategoryViewer();
$(function() { setInterval("viewer.queueStep()", 0); });
