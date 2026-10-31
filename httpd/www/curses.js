// emulate Curses library

var textArea1  = '';
var charWidth  = 0;
var charHeight = 0;

function initscr()  {
  charWidth  = Math.floor(document.getElementById("charWidth").getBoundingClientRect().width / 20);
  charHeight = Math.floor(document.getElementById("charWidth").getBoundingClientRect().height / 1);
}

function addstr(str) {
  textArea1 += str;
}

function addstr0(str) {
  document.getElementById("textArea0").innerHTML = str;
}

function cbreak() {
}

function clear() {
  textArea1 = '';
  refresh();
}

function curs_set(on) {
}

function echo() {
}

function flushinp() {
}

function getch() {
  return(''); // use document.onkeydown instead
}

function getmaxy() {
  return( Math.floor( Math.max(document.documentElement.clientHeight, window.innerHeight || 0) / charHeight ) -1);
}
function getmaxx() {
  return( Math.floor( Math.max(document.documentElement.clientWidth,  window.innerWidth  || 0) / charWidth ) -1);
}

function getstr(question) {
  return( prompt(question, '') );
}

function nocbreak() {
}

function nodelay(on) {
}

function noecho() {
}

function refresh() {
  document.getElementById("textArea1").innerHTML = textArea1;
  textArea1 = '';
}


// Perl built-ins
function ord(chr) {
  return(chr.charCodeAt(0));
}

function int(val) {
  return(Math.floor(val));
}

function uc(str) {
  return(str.toUpperCase());
}

function usleep(time) {
}

function x(str, cnt) {
  var out = '';
  for(var i=1;i<=cnt;i++) {
    out += str;
  }
  return(out);
}

// Javascript helpers
function Create2DArray(rows) {
  var arr = [];

  for (var i=0;i<rows;i++) {
     arr[i] = [];
  }

  return arr;
}

function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function rot13(s) {
  var s1 = s.replace(/[a-zA-Z]/g, function (c) { return String.fromCharCode((c <= "Z" ? 90 : 122) >= (c = c.charCodeAt(0) + 13) ? c : c - 26); });
  return (s1);
}

function escapeHTML(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* Do a foreach key in array:
for (key in array) {
  if (arrayHasOwnIndex(a, key)) {
    console.log( a[key] );
  }
}
*/
function arrayHasOwnIndex(array, prop) {
    return array.hasOwnProperty(prop) && /^0$|^[1-9]\d*$/.test(prop) && prop <= 4294967294; // 2^32 - 2
}
