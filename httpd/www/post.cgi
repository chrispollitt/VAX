#!/usr/bin/perl -w
# POST form: shows back what was typed in the box.
# (The old version of this page ran the text as Perl; this one only echoes it.)
use CGI;

my $q = CGI->new;
my $url = "/post.cgi";
print $q->header(-type => 'text/html'),
      $q->start_html('Hello World!');
my $mood = $q->param('Mood');
if (defined $mood) {
  print $q->h1('Thanks!'),
        $q->pre($q->escapeHTML($mood)),
        $q->hr(),
        $q->p('<a href="'.$url.'">again</a>');
}
else {
  print $q->script('
function validateForm() {
  var x=document.forms["Feeling"]["Mood"].value;
  if ( x==null || x=="" || !x.match(/[^ ]/) ) {
    alert("Please enter mood");
    return false;
  }
}
      '),
      $q->h1('Hello World!'),
      $q->p('And how are you doing today, '.scalar localtime().'?'),
      $q->start_form(
              -name     => 'Feeling',
              -action   => $url,
              -method   => 'post',
              -onsubmit => 'return validateForm()',
              ),
        $q->textarea(
          -name    => 'Mood',
          -default => 'Feeling fine',
          -rows    => 15,
          -columns => 60,
        ),
        $q->submit,
      $q->end_form();
}
print $q->end_html;
