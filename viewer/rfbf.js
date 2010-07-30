function catColors(x, y) {
  return [ Math.floor(80 + 80 * x), Math.floor(80 + 40 * y), Math.floor(80 - 80 * x) ];
}

function makeRfbfCell() {
  var cell = makeCell();
  cell.theSubtextD   = makeElement(cell, "span", "collapse dem");
  cell.theSubtextR   = makeElement(cell, "span", "collapse rep");
  cell.theSubtext    = $("span.collapse", cell);
  return cell;
}

function updateCell(info) {
  var text = info.concept, color = catColors(info.x, info.y);
  
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
    cell.theSubtext.text("");
  }
  if(cell.text == null)
    isold = true;
  
  text = this.checkCell(cell, text, this.images[text], 8, 8);
  
  if(text.indexOf(" #democrat") > -1)
    color = [0, 0, 255];
  if(text.indexOf(" #republican") > -1)
    color = [255, 0, 0];
  if(cell.type === "concept") {
    var subtext = info.text.split(" // ", 1)[0];
    if(info.text.indexOf(" #democrat") > 0)
      cell.theSubtextD.text("(D) " + subtext);
    if(info.text.indexOf(" #republican") > 0)
      cell.theSubtextR.text("(R) " + subtext);
  }
  
  cell.theText.css("fontSize", info.size * 100 + "pt").text(text);
  cell.doShow((1 + info.x) * 40, (1 - info.y) * 20, color, isold);
}

function start() {
  logo("fish.png", "red fish blue fish");
  viewer.images = { "#democrat": "donkey.png", "#republican": "elephant.png" };
  viewer.updateCell = updateCell;
  for(var i = 0; i < cellNum; i++)
    viewer.cellList.push(makeRfbfCell());
  $(function() { setInterval("viewer.queueStep()", 0); });
}
