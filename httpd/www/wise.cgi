#!/usr/bin/perl
# fortune + cowsay.  A normal CGI now: it prints its own header and uses print.
use CGI;
my $q = CGI->new;
print $q->header(-type => "text/html");
use Fortune;

$ROOT= 'CPVAX$DUA1:[system.bin.share.fortunes]';
$TOL = 0;
@fortunes = glob("$ROOT*.dat");
$TOL = scalar @fortunes;
$SELECT=int(rand($TOL));        # was rand($TOL)+1: could pick one past the end
($fortune_filename=$fortunes[$SELECT])=~s/\.dat$//i;
my $fortune_file = new Fortune ($fortune_filename);
$fortune_file->read_header ();
my $fortune = $fortune_file->get_random_fortune ();



##
## Cowsay 3.03
##
## This file is part of cowsay.  (c) 1999-2000 Tony Monroe.
##

use Text::Tabs qw(expand);
use Text::Wrap qw(wrap fill $columns);
use File::Basename;
use Getopt::Std;
use Cwd;

$version = "3.03";
$progname = basename($0);
$eyes = "oo";
$tongue = "  ";
$cowpath = 'CPVAX$DUA1:[system.bin.share.cows]';
@message = ($fortune);
@balloon_lines = ();
$thoughts = "";

## Yeah, this is rude, I know.  But hopefully it gets around a nasty
## little version dependency.

$Text::Wrap::initial_tab = 8;
$Text::Wrap::subsequent_tab = 8;
$Text::Wrap::tabstop = 8;

## One of these days, we'll get it ported to Windows.  Yeah, right.

$pathsep = ';';

%opts = (
    'e'		=>	'oo',
    'f'		=>	undef,
    'n'		=>	0,
    'T'		=>	'  ',
    'W'		=>	80,
);

$borg = $opts{'b'};
$dead = $opts{'d'};
$greedy = $opts{'g'};
$paranoid = $opts{'p'};
$stoned = $opts{'s'};
$tired = $opts{'t'};
$wired = $opts{'w'};
$young = $opts{'y'};
$eyes = substr($opts{'e'}, 0, 2);
$tongue = substr($opts{'T'}, 0, 2);
$the_cow = "default.cow";
$Text::Wrap::columns = $opts{'W'};

@message = ($opts{'n'} ? expand(@message) : 
	    split("\n", fill("", "", @message)));
&construct_balloon;
&construct_face;
&get_cow;
print $q->pre(@balloon_lines,$the_cow);

sub maxlength {
    my ($l, $m);
    $m = -1;
    for my $i (@_) {
	$l = length $i;
	$m = $l if ($l > $m);
    }
    return $m;
}

sub construct_balloon {
    my $max = &maxlength(@message);
    my $max2 = $max + 2;	## border space fudge.
    my $format = "%s %-${max}s %s\n";
    my @border;	## up-left, up-right, down-left, down-right, left, right
    if ($0 =~ /think/i) {
	$thoughts = 'o';
	@border = qw[ ( ) ( ) ( ) ];
    } elsif (@message < 2) {
	$thoughts = '\\';
	@border = qw[ < > ];
    } else {
	$thoughts = '\\';
	if ($V and $V gt v5.6.0) {		# Thanks, perldelta.
	    @border = qw[ / \\ \\ / | | ];
	} else {
	    @border = qw[ / \ \ / | | ];	
	}
    }
    push(@balloon_lines, 
	" " . ("_" x $max2) . " \n" ,
	sprintf($format, $border[0], $message[0], $border[1]),
	(@message < 2 ? "" : 
	    map { sprintf($format, $border[4], $_, $border[5]) } 
		@message[1 .. $#message - 1]),
	(@message < 2 ? "" : 
	    sprintf($format, $border[2], $message[$#message], $border[3])),
        " " . ("-" x $max2) . " \n"
    );
}

sub construct_face {
    if ($borg) { $eyes = "=="; }
    if ($dead) { $eyes = "xx"; $tongue = "U "; }
    if ($greedy) { $eyes = "\$\$"; }
    if ($paranoid) { $eyes = "@@"; }
    if ($stoned) { $eyes = "**"; $tongue = "U "; }
    if ($tired) { $eyes = "--"; } 
    if ($wired) { $eyes = "OO"; } 
    if ($young) { $eyes = ".."; }
}

sub get_cow {
##
## Get a cow from the specified cowfile; otherwise use the default cow
## which was defined above in $the_cow.
##
    my $f = $opts{'f'};
    my $full = "";
    if($opts{'r'}) {
      my $NUM = 0;
      my $TOL = 0;
      for my $c (glob("$cowpath*.cow")) {
        $TOL++;
      }
      my $SELECT=int(rand($TOL)+1);
      for $c (glob("$cowpath*.cow")) {
        $NUM++;
        if ( $NUM == $SELECT ) { $f=$c;last; }
      }
    }
    if ($f =~ m,\[,) {
	$full = $f;
    } else {
        if(defined $f) {
          1;
        }
        else {
          $f = $the_cow;
        } 
	for my $d (split(/$pathsep/, $cowpath)) {
	    if (-f "$d$f") {
		$full = "$d$f";
		last;
	    } elsif (-f "$d$f.cow") {
		$full = "$d$f.cow";
		last;
	    }
	}
	if ($full eq "") {
	    die "$progname: Could not find $f cowfile!\n";
	}
    }
    do $full;
    die "$progname: $@\n" if $@;
}


