
// *************************************************
// * LARGE letter NIL program - by CWP!inc (c)1994 *
// *************************************************

// TO DO:


"use strict";

var Ltr = Create2DArray(128);
var Srows,Scols;
var Lrows = 8;
var Lcols = 10;
var IntervalObj;
var Interval  = 15;


function App_Load() {
  var bgcolorlist=new Array("#FA8072", "#FFA500", "#F0E68C", "#7CFC00", "#7FFFD4",  "#EE82EE", "#FFF8DC");
  document.body.style.background=bgcolorlist[Math.floor(Math.random()*bgcolorlist.length)];

  initscr();
  DefAlpha();
  var a, g;
  
  // get screen size
  Scols = getmaxx();
  Srows = getmaxy();
  
  // generate link?
  g = getParameterByName('g');
  if (g.length != 0) {
    var a1;
    clear();
    a = getstr("Enter text: ") || '';
    clear();
    if (a.length != 0) {
      a1 = encodeURIComponent( rot13(a) );
      addstr0(window.location.href.split('?')[0] + "?a=" + a1);
    }
  }
  else {
    // get string from url
    if(msg) {
      a = decodeURIComponent(msg);
    }
    else {
      a = getParameterByName('a');
    }

    if (a.length == 0) {
      // ask for string
      clear();
      a = getstr("Enter text: ") || '';
      clear();
    }
    else {
      a = rot13(a);
      // strip from url
      var uri = window.location.toString();
      var clean_uri = uri.substring(0, uri.indexOf("?"));
      window.history.replaceState({}, document.title, clean_uri);
    }
  }

  // exit if empty
  if ( a.length == 0 ) {
    addstr( "<br>Exiting...<br>");
    refresh();
    return;
  }
  
  // add leading spaces
  a = x(" " , int(Scols/Lcols)) + uc(a);
  
  // Draw at regular intervals
  document.onkeydown = function (event) {
    event = event || window.event;
    var key = event.keyCode;
    if (key == 27) {
      document.onkeydown = null;
      clearInterval(IntervalObj);
      App_Load();
    }
  }
  LLprintStr = a;
  IntervalObj = setInterval(function () {
    LLprint();
  }, Interval);
    
}

var LLprintStr = '';
var LLprintJ = -1;
function LLprint() {
  
  // loop over Letter columns
  // for (var LLprintJ = 1; LLprintJ <= Lcols; LLprintJ++) {
  if(LLprintJ == -1) {
    LLprintJ = 1;
  }

    // loop over letter rows
    for (var k = 1; k <= Lrows; k++) {
      // first letter (full or partial)
      {
        var i = 1;
        //        ascii-code     srt  ln    srt len           row   col  
        //        of-letter      of-strg    of-char           screen
        PrintLtrP(ord(LLprintStr.substr( i-1, 1)), LLprintJ, Lcols+1 -LLprintJ, k);
      }
      // middle letters (full)
      for (var i = 2; i <= int(Scols/Lcols); i++) {
        PrintLtr(ord(LLprintStr.substr( i-1, 1)),  k);
      }
      // last letter (not at all, or partial)
      if (LLprintJ != 1) {
        var i = int(Scols/Lcols + 1);
        PrintLtrP(ord(LLprintStr.substr( i-1, 1)),  1, LLprintJ -1       , k);
      }
      addstr("<br>");
    }

    // update screen
    refresh();
    
  //}
  
  if(LLprintJ >= Lcols) {
    LLprintJ = -1;
    // move a along
    var a1 = LLprintStr.substr( 1) + LLprintStr.substr( 0 ,1);
    LLprintStr = a1;
  }
  else {
    LLprintJ++;
  }
}

function PrintLtr (a, k) {
  var x = Ltr[a][k]; 
  x = x.split("X").join("<span style='background: black'> </span>");
  addstr(x);
}

function PrintLtrP (a, b, e, k) {
  var x = Ltr[a][k].substr( b-1, e);
  x = x.split("X").join("<span style='background: black'> </span>");
  addstr(x);
}

function DefAlpha() {
  Ltr[32][1] = "          ";
  Ltr[32][2] = "          ";
  Ltr[32][3] = "          ";
  Ltr[32][4] = "          ";
  Ltr[32][5] = "          ";
  Ltr[32][6] = "          ";
  Ltr[32][7] = "          ";
  Ltr[32][8] = "          ";
 
  Ltr[33][1] = "   XX     "; // A+219 -> U+2588
  Ltr[33][2] = "   XX     ";
  Ltr[33][3] = "   XX     ";
  Ltr[33][4] = "   XX     ";
  Ltr[33][5] = "   XX     ";
  Ltr[33][6] = "          ";
  Ltr[33][7] = "   XX     ";
  Ltr[33][8] = "          ";
        
  Ltr[34][1] = " XX  XX   ";
  Ltr[34][2] = " XX  XX   ";
  Ltr[34][3] = "          ";
  Ltr[34][4] = "          ";
  Ltr[34][5] = "          ";
  Ltr[34][6] = "          ";
  Ltr[34][7] = "          ";
  Ltr[34][8] = "          ";
       
  Ltr[35][1] = "          ";
  Ltr[35][2] = " XX  XX   ";
  Ltr[35][3] = "XXXXXXXX  ";
  Ltr[35][4] = " XX  XX   ";
  Ltr[35][5] = " XX  XX   ";
  Ltr[35][6] = "XXXXXXXX  ";
  Ltr[35][7] = " XX  XX   ";
  Ltr[35][8] = "          ";
      
  Ltr[36][1] = "  X  X    ";
  Ltr[36][2] = " XXXXXXX  ";
  Ltr[36][3] = "X X  X    ";
  Ltr[36][4] = " XXXXXX   ";
  Ltr[36][5] = "  X  X X  ";
  Ltr[36][6] = "XXXXXXX   ";
  Ltr[36][7] = "  X  X    ";
  Ltr[36][8] = "          ";
      
  Ltr[37][1] = " X    X   ";
  Ltr[37][2] = "X X  X    ";
  Ltr[37][3] = " X  X     ";
  Ltr[37][4] = "   X      ";
  Ltr[37][5] = "  X  X    ";
  Ltr[37][6] = " X  X X   ";
  Ltr[37][7] = "X    X    ";
  Ltr[37][8] = "          ";
      
  Ltr[38][1] = "     X    ";
  Ltr[38][2] = "   XXXXX  ";
  Ltr[38][3] = "  X  X    ";
  Ltr[38][4] = "   XXXX   ";
  Ltr[38][5] = "  X  X    ";
  Ltr[38][6] = "   XXXXX  ";
  Ltr[38][7] = "     X    ";
  Ltr[38][8] = "          ";
       
  Ltr[39][1] = "   XX     ";
  Ltr[39][2] = "  XX      ";
  Ltr[39][3] = "          ";
  Ltr[39][4] = "          ";
  Ltr[39][5] = "          ";
  Ltr[39][6] = "          ";
  Ltr[39][7] = "          ";
  Ltr[39][8] = "          ";
       
  Ltr[40][1] = "     XX   ";
  Ltr[40][2] = "    XX    ";
  Ltr[40][3] = "   XX     ";
  Ltr[40][4] = "   XX     ";
  Ltr[40][5] = "   XX     ";
  Ltr[40][6] = "    XX    ";
  Ltr[40][7] = "     XX   ";
  Ltr[40][8] = "          ";
      
  Ltr[41][1] = "   XX     ";
  Ltr[41][2] = "    XX    ";
  Ltr[41][3] = "     XX   ";
  Ltr[41][4] = "     XX   ";
  Ltr[41][5] = "     XX   ";
  Ltr[41][6] = "    XX    ";
  Ltr[41][7] = "   XX     ";
  Ltr[41][8] = "          ";
      
  Ltr[42][1] = " X  X  X  "; // *
  Ltr[42][2] = "  X X X   ";
  Ltr[42][3] = "   XXX    ";
  Ltr[42][4] = " XXXXXXX  ";
  Ltr[42][5] = "   XXX    ";
  Ltr[42][6] = "  X X X   ";
  Ltr[42][7] = " X  X  X  ";
  Ltr[42][8] = "          ";
      
  Ltr[43][1] = "          ";
  Ltr[43][2] = "   XX     ";
  Ltr[43][3] = "   XX     ";
  Ltr[43][4] = "XXXXXXXX  ";
  Ltr[43][5] = "   XX     ";
  Ltr[43][6] = "   XX     ";
  Ltr[43][7] = "          ";
  Ltr[43][8] = "          ";

  Ltr[44][1] = "          ";
  Ltr[44][2] = "          ";
  Ltr[44][3] = "          ";
  Ltr[44][4] = "          ";
  Ltr[44][5] = "          ";
  Ltr[44][6] = "          ";
  Ltr[44][7] = "    XX    ";
  Ltr[44][8] = "   XX     ";

  Ltr[45][1] = "          ";
  Ltr[45][2] = "          ";
  Ltr[45][3] = "          ";
  Ltr[45][4] = "XXXXXXXX  ";
  Ltr[45][5] = "          ";
  Ltr[45][6] = "          ";
  Ltr[45][7] = "          ";
  Ltr[45][8] = "          ";

  Ltr[46][1] = "          "; // .
  Ltr[46][2] = "          ";
  Ltr[46][3] = "          ";
  Ltr[46][4] = "          ";
  Ltr[46][5] = "          ";
  Ltr[46][6] = "          ";
  Ltr[46][7] = "    XX    ";
  Ltr[46][8] = "          ";

  Ltr[47][1] = "      XX  ";
  Ltr[47][2] = "     XX   ";
  Ltr[47][3] = "    XX    ";
  Ltr[47][4] = "   XX     ";
  Ltr[47][5] = "  XX      ";
  Ltr[47][6] = " XX       ";
  Ltr[47][7] = "XX        ";
  Ltr[47][8] = "          ";
     
  Ltr[48][1] = " XXXXXX   ";
  Ltr[48][2] = "XX   XXX  ";
  Ltr[48][3] = "XX  X XX  ";
  Ltr[48][4] = "XX X  XX  ";
  Ltr[48][5] = "XXX   XX  ";
  Ltr[48][6] = "XX    XX  ";
  Ltr[48][7] = " XXXXXX   ";
  Ltr[48][8] = "          ";

  Ltr[49][1] = "   XX     ";
  Ltr[49][2] = "  XXX     ";
  Ltr[49][3] = "   XX     ";
  Ltr[49][4] = "   XX     ";
  Ltr[49][5] = "   XX     ";
  Ltr[49][6] = "   XX     ";
  Ltr[49][7] = "  XXXX    ";
  Ltr[49][8] = "          ";

  Ltr[50][1] = " XXXXXX   ";
  Ltr[50][2] = "XX    XX  ";
  Ltr[50][3] = "      XX  ";
  Ltr[50][4] = " XXXXXX   ";
  Ltr[50][5] = "XX        ";
  Ltr[50][6] = "XX        ";
  Ltr[50][7] = "XXXXXXXX  ";
  Ltr[50][8] = "          ";

  Ltr[51][1] = " XXXXXX   ";
  Ltr[51][2] = "XX    XX  ";
  Ltr[51][3] = "      XX  ";
  Ltr[51][4] = "   XXXX   ";
  Ltr[51][5] = "      XX  ";
  Ltr[51][6] = "XX    XX  ";
  Ltr[51][7] = " XXXXXX   ";
  Ltr[51][8] = "          ";

  Ltr[52][1] = "XX    XX  ";
  Ltr[52][2] = "XX    XX  ";
  Ltr[52][3] = "XX    XX  ";
  Ltr[52][4] = "XXXXXXXX  ";
  Ltr[52][5] = "      XX  ";
  Ltr[52][6] = "      XX  ";
  Ltr[52][7] = "      XX  ";
  Ltr[52][8] = "          ";

  Ltr[53][1] = "XXXXXXXX  ";
  Ltr[53][2] = "XX        ";
  Ltr[53][3] = "XX        ";
  Ltr[53][4] = "XXXXXXX   ";
  Ltr[53][5] = "      XX  ";
  Ltr[53][6] = "XX    XX  ";
  Ltr[53][7] = " XXXXXX   ";
  Ltr[53][8] = "          ";

  Ltr[54][1] = " XXXXXX   ";
  Ltr[54][2] = "XX    XX  ";
  Ltr[54][3] = "XX        ";
  Ltr[54][4] = "XXXXXXX   ";
  Ltr[54][5] = "XX    XX  ";
  Ltr[54][6] = "XX    XX  ";
  Ltr[54][7] = " XXXXXX   ";
  Ltr[54][8] = "          ";

  Ltr[55][1] = "XXXXXXXX  ";
  Ltr[55][2] = "     XX   ";
  Ltr[55][3] = "    XX    ";
  Ltr[55][4] = "   XX     ";
  Ltr[55][5] = "   XX     ";
  Ltr[55][6] = "   XX     ";
  Ltr[55][7] = "   XX     ";
  Ltr[55][8] = "          ";

  Ltr[56][1] = " XXXXXX   ";
  Ltr[56][2] = "XX    XX  ";
  Ltr[56][3] = "XX    XX  ";
  Ltr[56][4] = " XXXXXX   ";
  Ltr[56][5] = "XX    XX  ";
  Ltr[56][6] = "XX    XX  ";
  Ltr[56][7] = " XXXXXX   ";
  Ltr[56][8] = "          ";

  Ltr[57][1] = " XXXXXX   ";
  Ltr[57][2] = "XX    XX  ";
  Ltr[57][3] = "XX    XX  ";
  Ltr[57][4] = " XXXXXXX  ";
  Ltr[57][5] = "      XX  ";
  Ltr[57][6] = "XX    XX  ";
  Ltr[57][7] = " XXXXXX   ";
  Ltr[57][8] = "          ";

  Ltr[58][1] = "          ";
  Ltr[58][2] = "          ";
  Ltr[58][3] = "   XX     ";
  Ltr[58][4] = "          ";
  Ltr[58][5] = "          ";
  Ltr[58][6] = "   XX     ";
  Ltr[58][7] = "          ";
  Ltr[58][8] = "          ";
     
  Ltr[59][1] = "          ";
  Ltr[59][2] = "          ";
  Ltr[59][3] = "   XX     ";
  Ltr[59][4] = "          ";
  Ltr[59][5] = "          ";
  Ltr[59][6] = "          ";
  Ltr[59][7] = "   XX     ";
  Ltr[59][8] = "  XX      ";
     
  Ltr[60][1] = "      XX  ";
  Ltr[60][2] = "    XX    ";
  Ltr[60][3] = "  XX      ";
  Ltr[60][4] = "XX        ";
  Ltr[60][5] = "  XX      ";
  Ltr[60][6] = "    XX    ";
  Ltr[60][7] = "      XX  ";
  Ltr[60][8] = "          ";
     
  Ltr[61][1] = "          ";
  Ltr[61][2] = "          ";
  Ltr[61][3] = "XXXXXXXX  ";
  Ltr[61][4] = "          ";
  Ltr[61][5] = "XXXXXXXX  ";
  Ltr[61][6] = "          ";
  Ltr[61][7] = "          ";
  Ltr[61][8] = "          ";

  Ltr[62][1] = "XX        ";
  Ltr[62][2] = "  XX      ";
  Ltr[62][3] = "    XX    ";
  Ltr[62][4] = "      XX  ";
  Ltr[62][5] = "    XX    ";
  Ltr[62][6] = "  XX      ";
  Ltr[62][7] = "XX        ";
  Ltr[62][8] = "          ";
     
  Ltr[63][1] = "  XXXXX   ";
  Ltr[63][2] = " XX   XX  ";
  Ltr[63][3] = "      XX  ";
  Ltr[63][4] = "     XX   ";
  Ltr[63][5] = "    XX    ";
  Ltr[63][6] = "          ";
  Ltr[63][7] = "    XX    ";
  Ltr[63][8] = "          ";

  Ltr[64][1] = " XXXXXX   "; // @
  Ltr[64][2] = "X      X  ";
  Ltr[64][3] = "X  XX  X  ";
  Ltr[64][4] = "X X  X X  ";
  Ltr[64][5] = "X  XXXXX  ";
  Ltr[64][6] = "X         ";
  Ltr[64][7] = " XXXXX    ";
  Ltr[64][8] = "          ";
     
  Ltr[65][1] = "  XXXX    ";
  Ltr[65][2] = " XX  XX   ";
  Ltr[65][3] = "XX    XX  ";
  Ltr[65][4] = "XX    XX  ";
  Ltr[65][5] = "XXXXXXXX  ";
  Ltr[65][6] = "XX    XX  ";
  Ltr[65][7] = "XX    XX  ";
  Ltr[65][8] = "          ";

  Ltr[66][1] = "XXXXXXX   ";
  Ltr[66][2] = "XX    XX  ";
  Ltr[66][3] = "XX    XX  ";
  Ltr[66][4] = "XXXXXXX   ";
  Ltr[66][5] = "XX    XX  ";
  Ltr[66][6] = "XX    XX  ";
  Ltr[66][7] = "XXXXXXX   ";
  Ltr[66][8] = "          ";
 
  Ltr[67][1] = "  XXXX    ";
  Ltr[67][2] = " XX  XX   ";
  Ltr[67][3] = "XX        ";
  Ltr[67][4] = "XX        ";
  Ltr[67][5] = "XX        ";
  Ltr[67][6] = " XX  XX   ";
  Ltr[67][7] = "  XXXX    ";
  Ltr[67][8] = "          ";
 
  Ltr[68][1] = "XXXXXX    ";
  Ltr[68][2] = "XX   XX   ";
  Ltr[68][3] = "XX    XX  ";
  Ltr[68][4] = "XX    XX  ";
  Ltr[68][5] = "XX    XX  ";
  Ltr[68][6] = "XX   XX   ";
  Ltr[68][7] = "XXXXXX    ";
  Ltr[68][8] = "          ";
 
  Ltr[69][1] = "XXXXXXXX  ";
  Ltr[69][2] = "XX        ";
  Ltr[69][3] = "XX        ";
  Ltr[69][4] = "XXXXXX    ";
  Ltr[69][5] = "XX        ";
  Ltr[69][6] = "XX        ";
  Ltr[69][7] = "XXXXXXXX  ";
  Ltr[69][8] = "          ";
 
  Ltr[70][1] = "XXXXXXXX  ";
  Ltr[70][2] = "XX        ";
  Ltr[70][3] = "XX        ";
  Ltr[70][4] = "XXXXXX    ";
  Ltr[70][5] = "XX        ";
  Ltr[70][6] = "XX        ";
  Ltr[70][7] = "XX        ";
  Ltr[70][8] = "          ";
 
  Ltr[71][1] = "  XXXXX   ";
  Ltr[71][2] = " XX   XX  ";
  Ltr[71][3] = "XX        ";
  Ltr[71][4] = "XX        ";
  Ltr[71][5] = "XX   XXX  ";
  Ltr[71][6] = " XX   XX  ";
  Ltr[71][7] = "  XXXX X  ";
  Ltr[71][8] = "          ";
 
  Ltr[72][1] = "XX    XX  ";
  Ltr[72][2] = "XX    XX  ";
  Ltr[72][3] = "XX    XX  ";
  Ltr[72][4] = "XXXXXXXX  ";
  Ltr[72][5] = "XX    XX  ";
  Ltr[72][6] = "XX    XX  ";
  Ltr[72][7] = "XX    XX  ";
  Ltr[72][8] = "          ";
 
  Ltr[73][1] = "  XXXX    ";
  Ltr[73][2] = "   XX     ";
  Ltr[73][3] = "   XX     ";
  Ltr[73][4] = "   XX     ";
  Ltr[73][5] = "   XX     ";
  Ltr[73][6] = "   XX     ";
  Ltr[73][7] = "  XXXX    ";
  Ltr[73][8] = "          ";
 
  Ltr[74][1] = "    XXXX  ";
  Ltr[74][2] = "     XX   ";
  Ltr[74][3] = "     XX   ";
  Ltr[74][4] = "     XX   ";
  Ltr[74][5] = "     XX   ";
  Ltr[74][6] = "XX   XX   ";
  Ltr[74][7] = " XXXXX    ";
  Ltr[74][8] = "          ";
 
  Ltr[75][1] = "XX    XX  ";
  Ltr[75][2] = "XX   XX   ";
  Ltr[75][3] = "XX  XX    ";
  Ltr[75][4] = "XXXXX     ";
  Ltr[75][5] = "XX  XX    ";
  Ltr[75][6] = "XX   XX   ";
  Ltr[75][7] = "XX    XX  ";
  Ltr[75][8] = "          ";

  Ltr[76][1] = "XX        ";
  Ltr[76][2] = "XX        ";
  Ltr[76][3] = "XX        ";
  Ltr[76][4] = "XX        ";
  Ltr[76][5] = "XX        ";
  Ltr[76][6] = "XX        ";
  Ltr[76][7] = "XXXXXXXX  ";
  Ltr[76][8] = "          ";
 
  Ltr[77][1] = "XX    XX  ";
  Ltr[77][2] = "XXX  XXX  ";
  Ltr[77][3] = "XXXXXXXX  ";
  Ltr[77][4] = "XX XX XX  ";
  Ltr[77][5] = "XX    XX  ";
  Ltr[77][6] = "XX    XX  ";
  Ltr[77][7] = "XX    XX  ";
  Ltr[77][8] = "          ";

  Ltr[78][1] = "XX    XX  ";
  Ltr[78][2] = "XXX   XX  ";
  Ltr[78][3] = "XXXX  XX  ";
  Ltr[78][4] = "XX XX XX  ";
  Ltr[78][5] = "XX  XXXX  ";
  Ltr[78][6] = "XX   XXX  ";
  Ltr[78][7] = "XX    XX  ";
  Ltr[78][8] = "          ";

  Ltr[79][1] = "  XXXX    ";
  Ltr[79][2] = " XX  XX   ";
  Ltr[79][3] = "XX    XX  ";
  Ltr[79][4] = "XX    XX  ";
  Ltr[79][5] = "XX    XX  ";
  Ltr[79][6] = " XX  XX   ";
  Ltr[79][7] = "  XXXX    ";
  Ltr[79][8] = "          ";

  Ltr[80][1] = "XXXXXX    ";
  Ltr[80][2] = "XX   XX   ";
  Ltr[80][3] = "XX   XX   ";
  Ltr[80][4] = "XXXXXX    ";
  Ltr[80][5] = "XX        ";
  Ltr[80][6] = "XX        ";
  Ltr[80][7] = "XX        ";
  Ltr[80][8] = "          ";

  Ltr[81][1] = "  XXXX    ";
  Ltr[81][2] = " XX  XX   ";
  Ltr[81][3] = "XX    XX  ";
  Ltr[81][4] = "XX    XX  ";
  Ltr[81][5] = "XX  X XX  ";
  Ltr[81][6] = " XX  XX   ";
  Ltr[81][7] = "  XXXX X  ";
  Ltr[81][8] = "          ";
 
  Ltr[82][1] = "XXXXXX    ";
  Ltr[82][2] = "XX   XX   ";
  Ltr[82][3] = "XX   XX   ";
  Ltr[82][4] = "XXXXXX    ";
  Ltr[82][5] = "XX  XX    ";
  Ltr[82][6] = "XX   XX   ";
  Ltr[82][7] = "XX   XX   ";
  Ltr[82][8] = "          ";
 
  Ltr[83][1] = "  XXXXX   ";
  Ltr[83][2] = " XX   XX  ";
  Ltr[83][3] = " XX       ";
  Ltr[83][4] = "  XXXXX   ";
  Ltr[83][5] = "      XX  ";
  Ltr[83][6] = " XX   XX  ";
  Ltr[83][7] = "  XXXXX   ";
  Ltr[83][8] = "          ";

  Ltr[84][1] = "XXXXXXXX  ";
  Ltr[84][2] = "   XX     ";
  Ltr[84][3] = "   XX     ";
  Ltr[84][4] = "   XX     ";
  Ltr[84][5] = "   XX     ";
  Ltr[84][6] = "   XX     ";
  Ltr[84][7] = "   XX     ";
  Ltr[84][8] = "          ";

  Ltr[85][1] = "XX    XX  ";
  Ltr[85][2] = "XX    XX  ";
  Ltr[85][3] = "XX    XX  ";
  Ltr[85][4] = "XX    XX  ";
  Ltr[85][5] = "XX    XX  ";
  Ltr[85][6] = "XX    XX  ";
  Ltr[85][7] = " XXXXXX   ";
  Ltr[85][8] = "          ";
 
  Ltr[86][1] = "XX    XX  ";
  Ltr[86][2] = "XX    XX  ";
  Ltr[86][3] = "XX    XX  ";
  Ltr[86][4] = "XX    XX  ";
  Ltr[86][5] = " XX  XX   ";
  Ltr[86][6] = "  XXXX    ";
  Ltr[86][7] = "   XX     ";
  Ltr[86][8] = "          ";
 
  Ltr[87][1] = "XX    XX  ";
  Ltr[87][2] = "XX    XX  ";
  Ltr[87][3] = "XX    XX  ";
  Ltr[87][4] = "XX XX XX  ";
  Ltr[87][5] = "XXXXXXXX  ";
  Ltr[87][6] = "XXX  XXX  ";
  Ltr[87][7] = "XX    XX  ";
  Ltr[87][8] = "          ";
 
  Ltr[88][1] = "XX    XX  ";
  Ltr[88][2] = " XX  XX   ";
  Ltr[88][3] = "  XXXX    ";
  Ltr[88][4] = "   XX     ";
  Ltr[88][5] = "  XXXX    ";
  Ltr[88][6] = " XX  XX   ";
  Ltr[88][7] = "XX    XX  ";
  Ltr[88][8] = "          ";
 
  Ltr[89][1] = "XX    XX  ";
  Ltr[89][2] = " XX  XX   ";
  Ltr[89][3] = "  XXXX    ";
  Ltr[89][4] = "   XX     ";
  Ltr[89][5] = "   XX     ";
  Ltr[89][6] = "   XX     ";
  Ltr[89][7] = "   XX     ";
  Ltr[89][8] = "          ";

  Ltr[90][1] = "XXXXXXXX  "; // Z
  Ltr[90][2] = "     XX   ";
  Ltr[90][3] = "    XX    ";
  Ltr[90][4] = "   XX     ";
  Ltr[90][5] = "  XX      ";
  Ltr[90][6] = " XX       ";
  Ltr[90][7] = "XXXXXXXX  ";
  Ltr[90][8] = "          ";

  Ltr[91][1] = "  XXXX    "; // [
  Ltr[91][2] = "  X       ";
  Ltr[91][3] = "  X       ";
  Ltr[91][4] = "  X       ";
  Ltr[91][5] = "  X       ";
  Ltr[91][6] = "  X       ";
  Ltr[91][7] = "  XXXX    ";
  Ltr[91][8] = "          ";

  Ltr[92][1] = "XX        "; // \
  Ltr[92][2] = " XX       ";
  Ltr[92][3] = "  XX      ";
  Ltr[92][4] = "   XX     ";
  Ltr[92][5] = "    XX    ";
  Ltr[92][6] = "     XX   ";
  Ltr[92][7] = "      XX  ";
  Ltr[92][8] = "          ";

  Ltr[93][1] = "  XXXX    "; // ]
  Ltr[93][2] = "     X    ";
  Ltr[93][3] = "     X    ";
  Ltr[93][4] = "     X    ";
  Ltr[93][5] = "     X    ";
  Ltr[93][6] = "     X    ";
  Ltr[93][7] = "  XXXX    ";
  Ltr[93][8] = "          ";

  Ltr[94][1] = "    X     "; // ^
  Ltr[94][2] = "   X X    ";
  Ltr[94][3] = "  X   X   ";
  Ltr[94][4] = "          ";
  Ltr[94][5] = "          ";
  Ltr[94][6] = "          ";
  Ltr[94][7] = "          ";
  Ltr[94][8] = "          ";

  Ltr[95][1] = "          "; // _
  Ltr[95][2] = "          ";
  Ltr[95][3] = "          ";
  Ltr[95][4] = "          ";
  Ltr[95][5] = "          ";
  Ltr[95][6] = "          ";
  Ltr[95][7] = "XXXXXXXX  ";
  Ltr[95][8] = "          ";

  Ltr[96][1] = "   XX     "; // `
  Ltr[96][2] = "    XX    ";
  Ltr[96][3] = "          ";
  Ltr[96][4] = "          ";
  Ltr[96][5] = "          ";
  Ltr[96][6] = "          ";
  Ltr[96][7] = "          ";
  Ltr[96][8] = "          ";

  Ltr[123][1] = "    XX    "; // {
  Ltr[123][2] = "   X      ";
  Ltr[123][3] = "   X      ";
  Ltr[123][4] = "  X       ";
  Ltr[123][5] = "   X      ";
  Ltr[123][6] = "   X      ";
  Ltr[123][7] = "    XX    ";
  Ltr[123][8] = "          ";

  Ltr[124][1] = "   X      "; // |
  Ltr[124][2] = "   X      ";
  Ltr[124][3] = "   X      ";
  Ltr[124][4] = "   X      ";
  Ltr[124][5] = "   X      ";
  Ltr[124][6] = "   X      ";
  Ltr[124][7] = "   X      ";
  Ltr[124][8] = "          ";

  Ltr[125][1] = "  XX      "; // }
  Ltr[125][2] = "    X     ";
  Ltr[125][3] = "    X     ";
  Ltr[125][4] = "     X    ";
  Ltr[125][5] = "    X     ";
  Ltr[125][6] = "    X     ";
  Ltr[125][7] = "  XX      ";
  Ltr[125][8] = "          ";

  Ltr[126][1] = "          "; // ~
  Ltr[126][2] = "          ";
  Ltr[126][3] = " XX       ";
  Ltr[126][4] = "X  X  X   ";
  Ltr[126][5] = "    XX    ";
  Ltr[126][6] = "          ";
  Ltr[126][7] = "          ";
  Ltr[126][8] = "          ";
}

