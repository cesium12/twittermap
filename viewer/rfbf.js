function makeRfbfCell() {
  var cell = makeCell();
  for(var i = 0; i < _tags.length; i++)
    makeElement(cell, "span", "collapse").css("color", _tags[i][2]);
  cell.theSubtext = $(".collapse", cell);
  return cell;
}

function updateCell(info) {
  var text = info.concept, x = info.x, y = info.y, color = eval(_color);
  
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
    cell.theSubtext.html("");
  }
  if(cell.text === null)
    isold = true;
  
  var image = "";
  for(var i = 0; i < _tags.length; i++) {
    var tag = _tags[i][0], spacetag = " " + tag;
    if(text == tag)
      image = _tags[i][1];
    else if(text.indexOf(spacetag) > -1)
      color = _tags[i][2];
    if(info.text.indexOf(spacetag) > 0)
      $(cell.theSubtext[i]).html(_tags[i][3] + info.text.split(" // ", 1)[0]);
  }
  
  text = this.checkCell(cell, text, image, 8, 8);
  cell.doShow((1 + info.x) / 2, (1 - info.y) / 2, info.size * 100, text, color, isold);
}

function start(url, title) {
  logo(url, title);
  viewer.updateCell = updateCell;
  for(var i = 0; i < cellNum; i++)
    viewer.cellList.push(makeRfbfCell());
  setInterval("viewer.queueStep()", 0);
}
