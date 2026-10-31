#!/usr/bin/perl -w
use CGI;

my $q = CGI->new;
print $q->header(-type => 'text/html',
                 -access_control_allow_origin => '*'),
      $q->start_html('ping'),
      $q->h1('ping'),
      $q->p('ping'),
      $q->end_html;
