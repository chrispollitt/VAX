#!/usr/bin/perl -w
# GET form: asks for a mood, thanks you for it.
use CGI;

my $q = CGI->new;
my $url = "/test.cgi";
print $q->header(-type => 'text/html'),
      $q->start_html('Hello World!');
my $mood = $q->param('Mood');
if (defined $mood) {
  print $q->h1('Thanks!'),
        $q->p('Thanks for letting me know that you are feeling '.$q->escapeHTML($mood).'.');
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
              -method   => 'get',
              -onsubmit => 'return validateForm()',
              ),
        $q->textfield('Mood'),
        $q->submit,
      $q->end_form();
}
print $q->end_html;
