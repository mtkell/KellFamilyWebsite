#!/usr/bin/perl

# before anything else, the script needs to find out its own name
#
# some servers (notably IIS on windows) don't set the cwd to the script's
# directory before executing it.  So we get that information
# from $0 (the full name & path of the script).
BEGIN{($_=$0)=~s![\\/][^\\/]+$!!;push@INC,$_}

$name = $0;
$name =~ s/.+\/?.+\///;  # for unix
$name =~ s/.+\\.+\\//;  # for windows
$path = $0;
$path =~ s/(.+\/).+/$1/g;  # for unix
$path =~ s/(.+\\).+/$1/g;  # for windows

# The "use Cwd" method would be nice, but it doesn't work with 
# some versions of IIS/ActivePerl
#use Cwd;
#$path = cwd;

if ($path ne "")
{
  chdir $path;
  push @INC,$path;
}
# finished discovering name


# some global variables (more further down)
local $plans_version = "6.7.2";        # version
local $debug_info;
local %options;
local $perl_version = (sprintf ("%vd",$^V));
#local $options{data_storage_mode};
local $fatal_error = 0;          # fatal errors cause plans to abort and print an error message to the browser
local $error_info = "";        
local $html_output;
local $script_url = "";

local $template_html;
local $event_details_template;
local $list_item_template;
local $calendar_item_template;
local $upcoming_item_template;

local %calendars;
local %current_calendar;
local %latest_calendar;
local %latest_new_calendar;
local $max_cal_id = 0;
local $max_new_cal_id = 0;
local $max_series_id = 0;

local %events;
local %current_event;
local %latest_event;
local $max_event_id = 0;
local %text;
local %cookie_parms;
local $max_remote_event_id = 0;

local %discoveries;


local $options{default_template_path} = "";
local $theme_url = "";
local $options{choose_themes} = "";
local $graphics_url = "";
local $icons_url = "";
local $input_cal_id_valid = 0;
local $options{right_click_menus_enabled} = 0;
local %cal_options;

local $rightnow;
local @months;
local @months_abv;
local @day_names;
local $loaded_all_events;    # flag used to avoid calling load_events("all") twice
                             # not needed for calendars (we always load all calendars)

local @disabled_tabs;

# check for required modules.

my $module_found=0;
foreach $temp_path (@INC)
{
  if (-e "$temp_path/plans_config.pl")
    {$module_found=1;}
}
if ($module_found == 0)
{
  $fatal_error=1;
  $error_info .= "Unable to locate <b>plans_config.pl</b>!  It should be in the same directory as plans.cgi!\n";
}
else {require "plans_config.pl";}



$module_found=0;
foreach $temp_path (@INC)
{
  if (-e "$temp_path/CGI")
    {$module_found=1;}
}

if ($module_found == 0)
{
  $fatal_error=1;
  $error_info .= "unable to locate required module <b>CGI</b>!\n";
}
else
  {use CGI;}


$module_found=0;
foreach $temp_path (@INC)
{
  if (-e "$temp_path/CGI/Carp.pm")
    {$module_found=1;}
}

if ($module_found == 0)
{
  $fatal_error=1;
  $error_info .= "unable to locate required module <b>CGI::Carp</b>!\n";
}
else
  {use CGI::Carp qw/fatalsToBrowser/;}

$module_found=0;
foreach $temp_path (@INC)
{
  if (-e "$temp_path/Time")
    {$module_found=1;}
}

if ($module_found == 0)
{
  $fatal_error=1;
  $error_info .= "unable to locate required module <b>Time.pm</b>!\n";
}
else
  {use Time::Local;}

$module_found=0;
foreach $temp_path (@INC)
{
  if (-e "$temp_path/IO.pm")
    {$module_found=1;}
}
if ($module_found == 0)
{
  $fatal_error=1;
  $error_info .= "unable to locate required module <b>IO.pm</b>!\n";
}
else
  {use IO::Socket;}

if ($fatal_error == 1)  # print error and bail out
{
  &fatal_error();
}


$module_found=0;
foreach $temp_path (@INC)
{
  if (-r "$temp_path/plans_lib.pl")
    {$module_found=1;}
}
if ($module_found == 0)
{
  $fatal_error=1;
  $error_info .= "Unable to locate <b>plans_lib.pl</b>!  It should be in the same directory as plans.cgi!\n";
}
else {require "plans_lib.pl";}

# get the language file, if one is defined

if (defined $options{language_files})
{
  my @language_files = split(',', $options{language_files});

  foreach $language_file (@language_files)
  {

    $module_found=0;
    foreach $temp_path (@INC)
    {
      if (-r "$temp_path/$language_file")
        {$module_found=1;}
    }
    if ($module_found == 0)
    {
      $fatal_error=1;
      $error_info .= "Unable to locate language file <b>$language_file</b>!  It should be in the same directory as plans.cgi!\n";
    }
    else {require $language_file;}
  }
}
else
{
  $fatal_error=1;
  $error_info .= "No language files defined in plans.config!\n";
}

# check for perl version
my $temp = substr($perl_version,0,3);
if ($temp < 5.6) {
  $fatal_error=1;
  $error_info .= "Your version of perl ($perl_version) is too old!  Plans requires perl version 5.6 or better.\n";
}

if ($fatal_error == 1)  # print error and bail out
{
  &fatal_error();
}

# load discoveries
&load_discoveries();


# init cgi stuff
$q = new CGI;
$script_url = $q->url(-path_info>=1);
$script_url =~ /(.*)\//;          # remove trailing / and all text after
$script_url = $1;                 # remove trailing / and all text after

&new_discovery($script_url, "script_url");


%cookie_parms = %{&extract_cookie_parms()};

# check if data files or tables are present
&check_data();                         

# fatal error?  Print error and bail out
if ($fatal_error == 1)                  
  {&fatal_error();}

if ($options{choose_themes})
{
  $theme_url = $q->param('theme_url');
  $theme_url = $cookie_parms{'theme_url'} if ($theme_url eq "");
} 

if ($theme_url eq "")
  {$theme_url = "$script_url/theme";}

$graphics_url ="$theme_url/graphics";                      # where misc. graphics are 
$icons_url = "$theme_url/icons";                           # where icons are
$css_path = "$theme_url/plans.css";                         # css file

if ($theme_url eq "$script_url/theme" || $q->param('theme_url') eq "" && $cookie_parms{'theme_url'} eq "")
{
  &force_discovery($theme_url, "theme_url");
}

# globals for http parameters
my $active_tab = $q->param('active_tab') + 0; # +0 ensures numericity
$active_tab = 0 if ($active_tab >= scalar @tab_text);

my $add_edit_cal_action = $q->param('add_edit_cal_action');
$add_edit_cal_action = "" if (!&contains(["add", "edit", "view_pending"],$add_edit_cal_action));  # validate

my $add_edit_event = $q->param('add_edit_event');
$add_edit_event = "" if (!&contains(["add", "edit"],$add_edit_event));  # validate

local $current_event_id = $q->param('evt_id');
$current_event_id = "" if ($current_event_id !~ /^R?\d+$/);  # validate

local $cal_start_month = $q->param('cal_start_month') + 0; # +0 ensures numericity
local $cal_start_year = $q->param('cal_start_year') + 0;   # +0 ensures numericity
local $cal_num_months = $q->param('cal_num_months') + 0;   # +0 ensures numericity

# if view parameters not supplied in http request, check cookie
$cal_start_month = $cookie_parms{'cal_start_month'} if ($cal_start_month eq "");
$cal_start_year = $cookie_parms{'cal_start_year'} if ($cal_start_year eq "");
$cal_num_months = $cookie_parms{'cal_num_months'} if ($cal_num_months eq "");


my $special_action = $q->param('special_action');
local $display_type = $q->param('display_type') + 0;   # +0 ensures numericity
$display_type = $cookie_parms{'display_type'} if ($cal_start_month eq "");
$display_type = 0 if ($display_type eq "");


# other globals
my $event_start_date;
my $event_start_timestamp;
my $event_days;
my $start_mday;
my $start_mon;
my $start_year;
my @timestamp_array;
my $recur_end_timestamp;

# load calendar data
&load_calendars();

local $current_cal_id = $q->param('cal_id') + 0;  # +0 ensures numericity
$current_cal_id = $cookie_parms{'cal_id'} if ($current_cal_id eq "");

# if calendar id not supplied, but evt_id is supplied (like when viewing an event) use that event's calendar as the current calendar
#if ($current_event_id ne "")
#{
#  &load_event($current_event_id);
#  
#  my %temp_current_event = %{$events{$current_event_id}};
#  if ($current_cal_id eq "")
#  {
#    $current_cal_id = $temp_current_event{cal_ids}[0];
#  }
#}

foreach $cal_id (keys %calendars)
{
  if ($cal_id eq $current_cal_id)
    {$input_cal_id_valid = 1;}
}
    
if ($current_cal_id eq "")
  {$input_cal_id_valid = 0;}
  
if ($current_cal_id =~ /\D/)
  {$input_cal_id_valid = 0;}
  
$current_cal_id = 0 if ($current_event_id eq "" &&  !$input_cal_id_valid);

# make all calendars selectable by default
foreach $cal_id (keys %calendars)
  {$default_cal{selectable_calendars}{$cal_id} = 1;}

%current_calendar = %{$calendars{$current_cal_id}};

# time-related globals
$rightnow = time() + 3600 * $current_calendar{gmtime_diff};
@rightnow_array = gmtime $rightnow;
$rightnow_year = $rightnow_array[5]+1900;
$rightnow_month = $rightnow_array[4];
$rightnow_mday = $rightnow_array[3];
$next_year = $rightnow_year+1;
$rightnow_description = formatted_time($rightnow, "hh:mm:ss mn md yy");

@weekday_sequence = @day_names;

# custom stylesheet?
if ($current_calendar{custom_stylesheet} ne "")
{
  $css_path = "http://$current_calendar{custom_stylesheet}";
}

# if this is a custom calendar request, shoehorn the request parameters in
if ($q->param('custom_calendar') == 1)
{
  $current_cal_id = $q->param('custom_calendar_calendar') + 0;
  @custom_calendar_backgound_calendars = $q->param('custom_calendar_background_calendars');
  
  foreach $local_background_calendar (keys %{$calendars{$current_cal_id}{local_background_calendars}})
    {delete $calendars{$current_cal_id}{local_background_calendars}{$local_background_calendar};}
    
  foreach $local_background_calendar (@custom_calendar_backgound_calendars)
    {$calendars{$current_cal_id}{local_background_calendars}{$local_background_calendar} = 1;}
  
  %current_calendar = %{$calendars{$current_cal_id}};
}



# make sure we can select the current calendar
#$current_calendar{selectable_calendars}{$current_cal_id} = 1;


# set info window height & width
$current_calendar{info_window_size} ="400x400" if ($current_calendar{info_window_size} eq ""); # default
my ($info_window_width, $info_window_height) = split("x", $current_calendar{info_window_size});


# rotate weekday_sequence by the offset defined in the week start day.
for ($l1=0;$l1 < $current_calendar{week_start_day};$l1++)
  {push @weekday_sequence, (shift @weekday_sequence);}



# load background_colors
my @temp_lines = split ("\n", $event_background_colors);

foreach $temp_line (@temp_lines)
{
  if ($temp_line !~ /\w/) # skip any blank lines
    {next;}
    
  $temp_line =~ s/^\s+//;   
  my ($hex_color, $hex_color_title) = split (/,*\s+/, $temp_line, 2);
  if ($hex_color_title eq "")
    {$hex_color_title = "&nbsp;";}
    
  push @event_bgcolors, {color => $hex_color, title => $hex_color_title};
}


#load template
my $custom_template_file_found=1;
my $local_template_file = 0; # tells whether the template was loaded via a filesystem open or through a http request.

if ($current_calendar{custom_template} ne "")  # custom template
{
  $template_html = &get_remote_file("$current_calendar{custom_template}");

  if ($template_html !~ /###/)
  {
    $custom_template_file_found=0;
    $lang{custom_template_fail} =~ s/###template###/$current_calendar{custom_template}/;
    $debug_info .= "$lang{custom_template_fail}\n";
  }
}


if ($current_calendar{custom_template} eq "" || $custom_template_file_found ==0)
{
  if (!(-e "$options{default_template_path}"))
  {
    $fatal_error=1;
    $lang{default_template_fail} =~ s/###template###/$options{default_template_path}/;
    $error_info .= "$lang{default_template_fail}\n";
    &fatal_error();
  }
  else
  {
    open (FH, "$options{default_template_path}") || ($debug_info .="<br/>Unable to open default template file $options{default_template_path} for reading<br/>");
    flock FH,2;
    @template_lines=<FH>;
    close FH;
    $template_html = join "", @template_lines;
    $local_template_file = 1;
  }
}

# load templates
&load_templates();



# ssi-style includes in the template
if ($local_template_file)
{
  my $new_html = $template_html;
  
  $template_html =~ s/###include\s+(.+)###/&load_file($1)/ge;
  
  #while ($new_html =~ s/###include\s+(.+)###//g)
  if(0)
  {
    my $include_file=$1;
    if (-e $include_file)
    {
      open (FH, "$include_file") || ($debug_info .="<br/>unable to open include file $include_file for reading<br/>");
      flock FH,2;
      my @include_lines=<FH>;
      close FH;
      $include_html = join "", @include_lines;
    }
    $template_html =~ s/###include\s+(.+)###/$include_html/;
  }
}

sub load_file()
{
  my ($file)=@_;
  if (-e $file)
  {
    open (FH, "$file") || (return "unable to open include file $file for reading");
    flock FH,2;
    my @lines=<FH>;
    close FH;
    $text = join "", @lines;
    return $text;
  }
  else
  {
    return "file $file does not exist";
  }
}



if($options{choose_themes})
{
  my $theme_file="choose_theme.html";
  my $theme_html="";
  if (-e $theme_file)
  {
    open (FH, "$theme_file") || ($debug_info .="<br/>unable to open theme file $theme_file for reading<br/>");
    flock FH,2;
    my @theme_lines=<FH>;
    close FH;
    $theme_html = join "", @theme_lines;
  }
  $template_html =~ s/###choose theme###/$theme_html/;
}
else
{
  $template_html =~ s/###choose theme###//;
}

                            

#evaluate browser type and version
$_ = $ENV{HTTP_USER_AGENT};

if (/Mozilla/) {
  if (/Opera.([0-9\.]+)/) { $browser_type = 'Opera'; $browser_version=$1;}
  elsif (/MSIE.([0-9.]+)/) { $browser_type = 'IE'; $browser_version = $1;}
  elsif (/Mozilla\/([0-9\.]+)/) {$browser_type = 'Mozilla'; $browser_version=$1;
    if (($browser_version<5) || (/Netscape/)) {$browser_type = "Netscape";} }
  if (/\)[^0-9.]+[0-9]*[\/\ ]([0-9.]+)/) {$browser_version=$1;}
} elsif (/(\w+)\/([0-9\.]+)/) {$browser_type = $1; $browser_version = $2}

#evaluate, transform, tweak, adjust, modify input values
#$debug_info .= "browser type: $browser_type<br/>";


#if no month is selected, use the current month
if ($cal_start_month == 0 && $q->param('cal_start_month') eq "")
{
  $cal_start_month = $rightnow_month;
  #$cal_start_month = 2;
}

#if the input year is out of range use the current year
if (($cal_start_year+0) < 1902 || ($cal_start_year+0)> 2037)
{
  $cal_start_year = $rightnow_year;
}

$cal_num_months = 1 if ($cal_num_months < 1);
$cal_num_months = $current_calendar{default_number_of_months} if ($cal_num_months > $current_calendar{max_number_of_months});
$cal_num_months = 1 if ($cal_num_months > $current_calendar{max_number_of_months});

#calculate calendar end month and year
$cal_end_month = $cal_start_month;
$cal_end_year = $cal_start_year;
for ($l1=1;$l1<$cal_num_months;$l1++)
{
  $cal_end_month++;
  if ($cal_end_month == 12)
  {
    $cal_end_month=0;
    $cal_end_year++;
  }
}

#check to make sure num_months+cal_start_date doesn't go out of bounds
if ($cal_end_year < 1902 || $cal_end_year> 2037)
{
  $cal_end_year = $cal_start_year;
  $cal_end_month = $cal_start_month;
  $cal_num_months = 1;
}

# time window for loading events

my $cal_start_timestamp = timegm(0,0,0,1,$cal_start_month,$cal_start_year) - 2592000;
my $cal_end_timestamp = timegm(0,0,0,1,$cal_end_month,$cal_end_year) + 5184000;
if ($q->param('cal_start_timestamp') ne "" && $q->param('cal_start_timestamp') !~ /\D/)
  {$cal_start_timestamp = $q->param('cal_start_timestamp');}
if ($q->param('cal_end_timestamp') ne "" && $q->param('cal_end_timestamp') !~ /\D/)
  {$cal_end_timestamp = $q->param('cal_end_timestamp');}
  

#$debug_info .="start: $cal_start_timestamp\nend: $cal_end_timestamp\nrightnow: $rightnow\n";

# load event data, for main calendar and its background calendars
my @temp_calendars = ($current_cal_id);
foreach $local_background_calendar (keys %{$current_calendar{local_background_calendars}})
  {push @temp_calendars, $local_background_calendar;}

&load_events($cal_start_timestamp, $cal_end_timestamp, \@temp_calendars);
if ($current_event_id ne "")
{
  &load_event($current_event_id);
  %current_event = %{$events{$current_event_id}};
}


# load events from remote background calendars

if (scalar keys %{$current_calendar{remote_background_calendars}} > 0)
{
  $remote_calendars_status="";
  my $temp = scalar keys %{$current_calendar{remote_background_calendars}};
  foreach $remote_calendar_id (keys %{$current_calendar{remote_background_calendars}})
  {
    # pull in remote calendar name
    my $remote_calendar_url = $current_calendar{remote_background_calendars}{$remote_calendar_id}{url};
    $remote_calendar_complete_url = $remote_calendar_url;
    #$debug_info .= "remote calendar: $remote_calendar_complete_url\n";

    $remote_calendar_complete_url .= "?remote_calendar_request=1&cal_id=$current_calendar{remote_background_calendars}{$remote_calendar_id}{remote_id}&cal_start_year=$cal_start_year&cal_start_month=$cal_start_month&num_months=$cal_num_months";
    #$debug_info .= "remote calendar url: $remote_calendar_complete_url\n";

    my $xml_results = &get_remote_file($remote_calendar_complete_url);
    
    if ($xml_results =~ /<error>/)
    {
      $xml_results =~ s/</&lt;/g;
      $xml_results =~ s/>/&gt;/g;
    
      $debug_info .= "Error fetching remote calendar: $xml_results\n";
    }
    else
    {
      my %remote_calendars = %{&xml2hash($xml_results)};

      my $remote_cal_title=$remote_calendars{'xml'}{calendar}{title};
    
      my $temp=$xml_results;
      $temp=~ s/>/&gt;/g;
      $temp=~ s/</&lt;/g;
      #$debug_info .= "xml results: $temp\n";
      
      &load_remote_events($xml_results, $current_calendar{remote_background_calendars}{$remote_calendar_id});
    }
  }
}


# calculate previous X months range.
my $previous_cal_start_month = $cal_start_month - $cal_num_months;
my $previous_cal_start_year = $cal_start_year;
if ($previous_cal_start_month < 0)
{
  $previous_cal_start_year = $cal_start_year - 1 - int(abs($cal_num_months - $cal_start_month) / 12);
  $previous_cal_start_month = 12 - abs($previous_cal_start_month) % 12;
}

# for the case when num_months = 12 and start_month=0
if ($previous_cal_start_month == 12)
{
  $previous_cal_start_month=0;
  $previous_cal_start_year++;
}


# singular or plural?
if ($cal_num_months > 1)
{
  $prev_string = $lang{previous_months};
  $prev_string =~ s/###num###/$cal_num_months/;
}
else
{
  $prev_string = $lang{previous_month};
}


# calculate next X months range.
my $next_cal_start_month = $cal_start_month + $cal_num_months;
my  $next_cal_start_year = $cal_start_year;
if ($next_cal_start_month > 11)
{
  $next_cal_start_year = $cal_start_year + int(abs($cal_num_months + $cal_start_month) / 12);
  $next_cal_start_month = abs($cal_start_month + $cal_num_months) % 12;
}


# singular or plural?
if ($cal_num_months > 1)
{
  $next_string = $lang{next_months};
  $next_string =~ s/###num###/$cal_num_months/;
}
else
{
  $next_string = $lang{next_month};
}





if ($q->param('diagnostic_mode') eq "1")
{
  my $diagnostic_results = &diagnostic_info;
  
  
  $html_output = <<p1;
Cache-control: no-cache,no-store,private
Content-Type: text/html; charset=$lang{charset}\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">

<html>
<head>
<title>Diagnostic mode</title>
</head>
<body style="font-family: arial;">

<br/><br/>
<h2>Plans Diagnostic information</h2>
<br/><br/>
$diagnostic_results

<br/><br/>
<b>Debug info:</b><br/>
<div style="color=:#0000ff;">
$debug_info
</div>
</body>
</html>

p1

  print $html_output;

  exit(0);
}

if ($q->param('detect_remote_calendars') eq "1")
{
  &detect_remote_calendars();
  exit(0);
}

if ($q->param('remote_calendar_request') eq "1")
{
  &remote_calendar_request();
  exit(0);
}

if ($q->param('export_calendar') eq "1")
{
  &normalize_timezone();
  if ($q->param('export_type') eq "ascii_text")
  {
    &ascii_text_cal($cal_start_month, $cal_start_year, $cal_end_month, $cal_end_year);
    exit(0);
  }
  elsif ($q->param('export_type') eq "csv_file")
  {
    &csv_file($cal_start_month, $cal_start_year, $cal_end_month, $cal_end_year);
    exit(0);
  }
  elsif ($q->param('export_type') eq "csv_file_palm")
  {
    &csv_file_palm($cal_start_month, $cal_start_year, $cal_end_month, $cal_end_year);
    exit(0);
  }
  elsif ($q->param('export_type') eq "vcalendar")
  {
    &vcalendar_export_cal($cal_start_month, $cal_start_year, $cal_end_month, $cal_end_year);
    exit(0);
  }
}

if ($q->param('export_event') eq "1")
{
  if ($q->param('export_type') eq "ascii_text")
  {
    &ascii_text_event();
    exit(0);
  }
  elsif ($q->param('export_type') eq "icalendar")
  {
    &icalendar_export_event();
    exit(0);
  }
  elsif ($q->param('export_type') eq "vcalendar")
  {
    &vcalendar_export_event();
    exit(0);
  }
}
elsif ($q->param('view_event') eq "1")
{
  &view_event();
  exit(0);
}
elsif ($q->param('email_reminder') eq "1")
{
  &email_reminder_prompt();
  exit(0);
}
elsif ($q->param('email_reminder_confirm') eq "1")
{
  &email_reminder_confirm();
  exit(0);
}
elsif ($special_action eq "preview_event")
{
  &preview_event();
  exit(0);
}
elsif ($special_action eq "preview_date")
{
  &preview_date();
  exit(0);
}

  my $view_cookie = &xml_store($cal_start_month, "cal_start_month");
  $view_cookie .= &xml_store($cal_start_year, "cal_start_year");
  $view_cookie .= &xml_store($cal_num_months, "cal_num_months");
  $view_cookie .= &xml_store($current_cal_id, "cal_id");
  $view_cookie .= &xml_store($display_type, "display_type");
  $view_cookie .= &xml_store($theme_url, "theme_url");

  $cookie_text = "Set-Cookie: plans_view=$view_cookie; path=/;";

  #$debug_info .= "cookie: $cookie_text\n";

  $html_output .=<<p1;
Cache-control: no-cache,no-store,private
Content-Type: text/html; charset=$lang{charset}
###cookie_text###\n

$template_html
p1

  $html_output =~ s/###current calendar title###/$current_calendar{title}/g;
  $html_output =~ s/###calendar\{(\d+)\}\{(.+?)\}###/$calendars{$1}{$2} if ($2 ne 'admin_password')/ge;
  $html_output =~ s/###event\{(\d+)\}\{(.+?)\}###/$events{$1}{$2}/ge;

  $insert_text =<<p1;
<script type="text/javascript" ><!--
###common javascript###
###page-specific javascript###
###browser-specific javascript###
//-->
</script>
p1
  chomp $insert_text;
  $html_output =~ s/###javascript stuff###/$insert_text/;

#default page
&display_default();

exit(0);




sub display_default
{
  chomp $insert_text;
  $html_output =~ s/###css file###/$css_path/g;
  
  
  # tab menu stuff
 $menu_tabs[0] = {status => "inactive",
                  html => "<a href=\"$script_url/$name?active_tab=0\">$tab_text[0]</a>"};
 $menu_tabs[1] = {status => "inactive",
                  html => "<a href=\"$script_url/$name?active_tab=1\">$tab_text[1]</a>"};
 $menu_tabs[2] = {status => "inactive",
                  html => "<a href=\"$script_url/$name?active_tab=2\">$tab_text[2]</a>"};

 $menu_tabs[$active_tab]{status} ="active";
                  
 $menu_tabs[2]{html} = "<a href=\"$script_url/$name?active_tab=2\">$tab_text[2]</a>";

 $insert_text =<<p1;
<br/>
<div style="padding:0px;margin:0px;margin-left:20px;white-space:nowrap;">
p1

  # this kludge sucks!  
  if ($browser_type eq "IE")
    {$tab_vert_offset=4;}
  else
    {$tab_vert_offset=0;}
  
  #lay out the actual menu tabs
  for ($l1=0;$l1<scalar @tab_text;$l1++)
  {
    if (&contains (\@disabled_tabs, $l1)) 
      {next;}
    $menu_tab = $menu_tabs[$l1];
    my $style="";
   
   #$tab_vert_offset=0;
    
   if ($$menu_tab{status} eq "active")
   {
     $style="top:".($tab_vert_offset-3)."px;padding-top:5px;padding-bottom:5px;margin-top:0;height:2em;";
   }
   else
   {
     $style="top:".($tab_vert_offset-3)."px;padding-top:3px;padding-bottom:4px;margin-top:1px;height:2em;";
   }
    $insert_text .=<<p1;
<span class="$$menu_tab{status}_tab" style="position:relative;border-bottom-width:0px;padding-top:5px;margin-bottom:0;margin-left:5px;margin-right:2px;white-space:nowrap;text-align:center;$style"> &nbsp; &nbsp; &nbsp; $$menu_tab{html} &nbsp; &nbsp; &nbsp; </span>
p1
   
    $noinsert_text .=<<p1;
<span class="$$menu_tab{status}_tab" style="position:relative;$style">$$menu_tab{html} &nbsp; &nbsp; &nbsp; </span>
p1
  }
  
  $insert_text .=<<p1;
</div>
p1
  chomp $insert_text;


    if ($q->param('custom_calendar') == 1)
    {
      $html_output =~ s/###tab menu stuff###//g;
    }
    else
    {
      $html_output =~ s/###tab menu stuff###/$insert_text/g;
    }
    
    
  $insert_text ="";

  #invisible html for context menu  
    $insert_text .=<<p1;
<div id="contextmenu" class="contextmenu" style="visibility:hidden;">
</div>
p1

  #main box stuff
  $insert_text .=<<p1;
p1

  #finished displaying tab menus, now time to display the appropriate stuff for
  #the selected tab

  if ($active_tab eq "0") #the first tab is the main calendar view
  {
    my $cal_controls_text =<<p1;
<div class="calendar_controls">
<form name="tab0_form" action="$script_url/$name" method="get">

<div style="float:right;margin:5px;padding:2px;vertical-align:middle;">
<input id="controls_submit_button" type="submit" value="$lang{controls_change}"/>
</div>

<div style="margin:5px;padding:2px;text-align:right;float:right;">
$lang{controls_start_month}: 
<select name="cal_start_month" onChange="blink('controls_submit_button', 3, 0);">
p1
    #list each month in the year
    $month_index=0;
    foreach $possible_month (@months)
    {
      if ($cal_start_month eq $month_index)
      {
        $cal_controls_text .=<<p1;
<option value="$month_index" selected>$possible_month
p1
      }
      else
      {
        $cal_controls_text .=<<p1;
<option value="$month_index">$possible_month
p1
      }
      $month_index++;
    }
    $cal_controls_text .=<<p1;
</select>
<input name="cal_start_year" value = "$cal_start_year" size=4 onChange="blink('controls_submit_button', 3, 0);"/><br/>
$lang{controls_num_months}
<input name="cal_num_months" value = "$cal_num_months" size=3 onChange="blink('controls_submit_button', 3, 0);"/>
</div>
p1
      $cal_controls_text .=<<p1;
<div class="calendar_select" style="margin:5px;padding:2px;float:left;text-align:left;">
$lang{controls_calendar_label}<br/>
p1

    my $num_selectable_calendars = scalar keys %{$current_calendar{selectable_calendars}};
    
    my @selectable_calendars;
    if ($options{all_calendars_selectable})
    {
      @selectable_calendars = keys %calendars;
    }
    else
    {
      @selectable_calendars = keys %{$current_calendar{selectable_calendars}};
    }
    
    
    if (scalar @selectable_calendars > 0)
    {
      $cal_controls_text .=<<p1;
<select name="cal_id" onChange="blink('controls_submit_button', 3, 0);">
p1
  
  
      #list each calendar for the user to select
      my %explicit_calendar_order;
      if ($options{calendar_select_order} ne "alpha" && $options{calendar_select_order} ne "")
      {
        my @cal_order_ids = split(',',$options{calendar_select_order});
        my $cal_order_index = 0;
        foreach $cal_order_id (@cal_order_ids)
        {
          $explicit_calendar_order{$cal_order_id} = $cal_order_index;
          $cal_order_index++;
        }
      }

      foreach $selectable_calendar_id (sort {
                                        if ($options{calendar_select_order} eq "alpha")
                                        {
                                          return lc $calendars{$a}{title} cmp lc $calendars{$b}{title};
                                        }
                                        elsif ($options{calendar_select_order} ne "")
                                          {return $explicit_calendar_order{$a} <=> $explicit_calendar_order{$b};}
                                        else
                                          {return $a <=> $b;}
                                        
                                      }  @selectable_calendars)
      {
        my $selected ="";
        $selected =" selected" if ($selectable_calendar_id eq $current_calendar{id});
        $selectable_calendar_id=~ s/\D//g;
        
        $cal_controls_text .=<<p1;
<option value = "$selectable_calendar_id"$selected>$calendars{$selectable_calendar_id}{title}
p1
      }
  
      $cal_controls_text .=<<p1;
</select>
p1
    }
    else
    {
      $cal_controls_text .=<<p1;
<span style="font-weight:bold;">$current_calendar{title}</span>
<input type="hidden" name="cal_id" value="$current_calendar{id}"/>
p1
    }
      $cal_controls_text .=<<p1;
</div>
p1
    
    
    $cal_controls_text .=<<p1;
<div style="margin:5px;padding:2px;float:left;text-align:left;">
$lang{controls_display_label}<br/>
<select name="display_type" onChange="blink('controls_submit_button', 3, 0);">
p1
    #foreach $possible_display_type (@{$options{display_types}})
    for (my $l1=0;$l1<scalar @{$options{display_types}};$l1++)
    {
      if ($options{display_types}[$l1] ne "1")
        {next};
      my $selected="";
      
      if ($l1 eq $display_type) 
        {$selected = "selected";}
        
      $cal_controls_text .=<<p1;
<option value="$l1" $selected>$lang{controls_display_type}[$l1]
p1
    }
    $cal_controls_text .=<<p1;
</select>
</div>
p1



    $cal_controls_text .=<<p1;
<br style="clear:both;"/>
</form>
</div>
p1
    if ($q->param('custom_calendar') == 1)
    {
      $html_output =~ s/###calendar controls###//g;
    }
    else
    {
      $html_output =~ s/###calendar controls###/$cal_controls_text/g;
    }
    
    $insert_text .= &do_calendar_list_view();  
    
    #select event range
    
    $cal_month_start_date = timegm(0,0,0,1,$cal_start_month,$cal_start_year);
    @cal_month_start_date_array = gmtime $cal_month_start_date;
  
    $events_start_timestamp = $cal_month_start_date - 604800;                            # +7 day margin
    $events_end_timestamp = &find_end_of_month($cal_end_month, $cal_end_year) + 604800;  # +7 day margin
      
    #now that we have selected the appropriate events, we can 
    #generate the corresponding javascript and calendar view
    #and insert/add it to the html output.
    $common_javascript = &common_javascript();
    $page_javascript = &calendar_view_javascript($events_start_timestamp, $events_end_timestamp);
  
    #display browser-appropriate javascript
    if ($browser_type eq "IE" || $browser_type eq "Opera")
      {$browser_javascript = &IE_javascript();}
    else
      {$browser_javascript = &NS6_javascript();}
    
    #replace javascript placeholders with actual html/javascript code

    $html_output =~ s/###common javascript###/$common_javascript/;
    $html_output =~ s/###page-specific javascript###/$page_javascript/;
    $html_output =~ s/###browser-specific javascript###/$browser_javascript/;
    
    my $temp1 .=<<p1;
<a class="prev_next" href="$script_url/$name?cal_id=$current_cal_id&amp;display_type=$display_type&amp;cal_start_month=$previous_cal_start_month&amp;cal_start_year=$previous_cal_start_year&amp;cal_num_months=$cal_num_months ">$prev_string</a>
p1
    my $temp2 .=<<p1;
<a class="prev_next" href="$script_url/$name?cal_id=$current_cal_id&amp;display_type=$display_type&amp;cal_start_month=$next_cal_start_month&amp;cal_start_year=$next_cal_start_year&amp;cal_num_months=$cal_num_months">$next_string</a>
p1
    $html_output =~ s/###previous month link###/$temp1/g;
    $html_output =~ s/###next month link###/$temp2/g;
    
  }
  elsif ($active_tab eq "1") #the second tab is the add/edit events view
  {
    $html_output =~ s/###calendar controls###//;

    $insert_text .=<<p1;
<form id="add_event_form" name="add_event_form" action="$script_url/$name" method="POST">
<input type="hidden" name="active_tab" value="1"/>
<input type="hidden" name="special_action" value=""/>
<input type="hidden" name="add_edit_event" value="$add_edit_event"/>
<input type="hidden" name="evt_id" value="$current_event_id"/>
p1
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      # some browsers sneak these in 
      $cal_link =~ s/\r//g;                  # some browsers sneak these in 
      $cal_details =~ s/\r//g;               # some browsers sneak these in 


      #check for required fields
      if ($cal_title eq "")
      {
        $cal_valid=0;
        push @results_messages, $lang{update_cal_error5};
      }
      
      #strip all html from label field
      if ($cal_title =~ m/<(.*)>/)
      {
        push @results_messages, $lang{update_cal_error6};
        $cal_title =~ s/<(.*)>//g;
      }
      
      $cal_link =~ s/http:\/\///g;  #strip http:// from link field



      #check for date format
      if ($date_format !~ /^(mm|dd|yy)\W(mm|dd|yy)\W(mm|dd|yy)$/ )
      {
        $cal_valid=0;
        push @results_messages, $lang{update_cal_error6_5};
      }

      if ($add_edit_cal_action eq "edit")
      {
        if ($options{disable_passwords} ne "1")
        {
          #this action is an edit of an existing calendar, so we need to make a replacement.
          if (!(defined $calendars{$cal_id}))
          {
            $cal_valid=0;
            push @results_messages, $lang{update_cal_error7};
          }
          else
          {
            #check password
            $input_password = crypt($cal_password, substr($cal_password, 0, 2));
 
            if ($input_password ne $calendars{$cal_id}{password} && $input_password ne $master_password)
            {
              $cal_valid=0;
               push @results_messages, "$lang{update_cal_error1} <b>$calendars{$cal_id}{title}</b>";
            }
          }
 
          #check for new password
          if ($new_cal_password ne "" || $repeat_new_cal_password ne "")
          {
            if ($new_cal_password ne $repeat_new_cal_password)
            {
              $cal_valid=0;
              push @results_messages, $lang{update_cal_error8};
            }
            else
            {
              $calendars{$cal_id}{password} = crypt($new_cal_password, substr($new_cal_password, 0, 2));
            }
          }
        }
        
        
        
        # check for gmtime_diff field
        if ($options{force_single_timezone} eq "1" && $cal_id ne "0")
        {
          $gmtime_diff = $calendars{0}{gmtime_diff}
        }

        
        # encrypt remote calendar password
        $remote_calendar_requests_password = crypt($remote_calendar_requests_password, substr($remote_calendar_requests_password, 0, 2));
        
        
        if ($cal_valid == 1)
        { # update calendar record
          my $xml_data = "";
          $calendars{$cal_id}{title} = $cal_title;
          $calendars{$cal_id}{details} = $cal_details;
          $calendars{$cal_id}{link} = $cal_link;
          $calendars{$cal_id}{new_calendars_automatically_selectable} = $new_calendars_automatically_selectable;
          $calendars{$cal_id}{list_background_calendars_together} = $list_background_calendars_together;
          $calendars{$cal_id}{calendar_events_color} = $calendar_events_color;
          $calendars{$cal_id}{background_events_display_style} = $background_events_display_style;
          $calendars{$cal_id}{background_events_fade_factor} = $background_events_fade_factor;
          $calendars{$cal_id}{background_events_color} = $background_events_color;
          $calendars{$cal_id}{default_number_of_months} = $default_number_of_months;
          $calendars{$cal_id}{max_number_of_months} = $max_number_of_months;
          $calendars{$cal_id}{gmtime_diff} = $gmtime_diff;
          $calendars{$cal_id}{date_format} = $date_format;
          $calendars{$cal_id}{week_start_day} = $week_start_day;
          $calendars{$cal_id}{preload_event_details} = $preload_event_details;
          $calendars{$cal_id}{info_window_size} = $info_window_size;
          $calendars{$cal_id}{custom_template} = $custom_template;
          $calendars{$cal_id}{custom_stylesheet} = $custom_stylesheet;
          $calendars{$cal_id}{allow_remote_calendar_requests} = $allow_remote_calendar_requests;
          $calendars{$cal_id}{remote_calendar_requests_require_password} = $remote_calendar_requests_require_password;
          $calendars{$cal_id}{remote_calendar_requests_password} = $remote_calendar_requests_password;

          
          # update local background calendars            
          foreach $local_background_calendar (keys %{$calendars{$cal_id}{local_background_calendars}})
            {delete $calendars{$cal_id}{local_background_calendars}{$local_background_calendar};}
          foreach $local_background_calendar (@local_background_calendars)
            {$calendars{$cal_id}{local_background_calendars}{$local_background_calendar} = 1;}

          #$debug_info .= "new remote calendars xml: $new_remote_calandars_xml\n";
          
          #delete existing remote background calendars
          
          foreach $current_remote_calendar_id (keys %{$current_calendar{remote_background_calendars}})
          {
            if ($q->param("delete_remote_calendar_$current_remote_calendar_id") ne "")
            {
              my $temp = $lang{get_remote_calendar5};
              $temp =~ s/###remote url###/$current_calendar{remote_background_calendars}{$current_remote_calendar_id}{url}/g;
              $temp =~ s/###remote id###/$current_calendar{remote_background_calendars}{$current_remote_calendar_id}{remote_id}/g;
              push @results_messages, $temp;
              
              delete $calendars{$current_cal_id}{remote_background_calendars}{$current_remote_calendar_id};
            }
          }
          
          
          
          # update remote background calendars
          unless ($new_remote_calandars_xml eq "")
          {
            my %new_remote_calendars = %{&xml2hash($new_remote_calandars_xml)};
            #$debug_info .= "$new_remote_calendars{remote_calendars}{remote_calendar}\n";
 
            my $new_remote_cal_id = &max(keys %{$calendars{$cal_id}{remote_background_calendars}}) + 1;
            $debug_info .= (scalar keys %{$calendars{$cal_id}{remote_background_calendars}})." remote calendars already\n";
            #$debug_info .= "new_remote_cal_id: $new_remote_cal_id\n";
            
            if ($new_remote_calendars{remote_calendars}{remote_calendar} =~ /array/i) # multiple remote background calendars
            {
              #$debug_info .= "multiple new remote calendars\n";
            
              foreach $temp (@{$new_remote_calendars{remote_calendars}{remote_calendar}})
              {
                my %new_remote_calendar = %{$temp};
                
                $found=0;
                foreach $current_remote_calendar_id (keys %{$current_calendar{remote_background_calendars}})
                {
                  #$debug_info .= "comparing $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{url} with $new_remote_calendar{url}\n";

                  if ($current_calendar{remote_background_calendars}{$current_remote_calendar_id}{url} eq $new_remote_calendar{url} &&
                      $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{type} eq $new_remote_calendar{type} &&
                      $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{version} eq $new_remote_calendar{version} &&
                      $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{password} eq $new_remote_calendar{password} &&
                      $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{remote_id} eq $new_remote_calendar{remote_id})
                        {$found=1;}
                }
                if ($found==0)
                {
                  $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{url} = $new_remote_calendar{url};
                  $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{type} = $new_remote_calendar{type};
                  $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{version} = $new_remote_calendar{version};
                  $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{password} = $new_remote_calendar{password};
                  $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{remote_id} = $new_remote_calendar{remote_id};
                  $new_remote_cal_id++;
                }
                else
                {
                  my $temp = $lang{get_remote_calendar4};
                  $temp =~ s/###remote url###/$new_remote_calendar{url}/g;
                  $temp =~ s/###remote id###/$new_remote_calendar{remote_id}/g;
                  push @results_messages, $temp;
                }
   
                #$debug_info .= "remote calendar: $new_remote_calendar{url}\n";
                #$debug_info .= "type: $new_remote_calendar{type}\n";
              }
            }
            else # single remote background calendar
            {
              # check against existing remote background calendars.
            
              my %new_remote_calendar = %{$new_remote_calendars{remote_calendars}{remote_calendar}};
            
              $found=0;
              foreach $current_remote_calendar_id (keys %{$current_calendar{remote_background_calendars}})
              {
                #$debug_info .= "comparing $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{url} with $new_remote_calendar{url}\n";
                if ($current_calendar{remote_background_calendars}{$current_remote_calendar_id}{url} eq $new_remote_calendar{url} && 
                    $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{type} eq $new_remote_calendar{type} &&
                    $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{version} eq $new_remote_calendar{version} &&
                    $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{password} eq $new_remote_calendar{password} &&
                    $current_calendar{remote_background_calendars}{$current_remote_calendar_id}{remote_id} eq $new_remote_calendar{remote_id})
                      {$found=1;}
              }
              if ($found==0)
              {
                $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{url} = $new_remote_calendar{url};
                $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{type} = $new_remote_calendar{type};
                $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{version} = $new_remote_calendar{version};
                $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{password} = $new_remote_calendar{password};
                $calendars{$cal_id}{remote_background_calendars}{$new_remote_cal_id}{remote_id} = $new_remote_calendar{remote_id};
              }
              else
              {
                my $temp = $lang{get_remote_calendar4};
                  $temp =~ s/###remote url###/$new_remote_calendar{url}/g;
                  $temp =~ s/###remote id###/$new_remote_calendar{remote_id}/g;
                push @results_messages, $temp;
              }
            }
          }
                    
          #$calendars{$cal_id}{remote_background_calendars} = $remote_calendar_requests_password;

            
          # update selectable calendars            
          foreach $selectable_calendar (keys %{$calendars{$cal_id}{selectable_calendars}})
            {delete $calendars{$cal_id}{selectable_calendars}{$selectable_calendar};}
          foreach $selectable_calendar (@selectable_calendars)
            {$calendars{$cal_id}{selectable_calendars}{$selectable_calendar} = 1;}
        
          # make sure the calendar can select itself.
          if (scalar keys %{$calendars{$cal_id}{selectable_calendars}} > 0)
            {$calendars{$cal_id}{selectable_calendars}{$cal_id} = 1;}
        }
        
        if ($cal_valid == 1)
        { #all checks successful, add/update calendar!
  
          &update_calendar($cal_id);
          push @results_messages, "<b>$calendars{$current_cal_id}{title}</b> $lang{update_cal_success}";
        }
        else
        {$cal_add_results .= $lang{update_cal_failure};}

      }
      else  # add new calendar
      {     
        #check new password
        if ($options{disable_passwords} ne "1")
        {
          if ($new_cal_password ne $repeat_new_cal_password)
          {
            $cal_valid=0;
            push @results_messages, $lang{update_cal_error9};
          }
          elsif ($new_cal_password eq "" || $repeat_new_cal_password eq "" )
          {
            $cal_valid=0;
            push @results_messages, $lang{update_cal_error10};
          }
          else
          {
            $input_password = crypt($new_cal_password, substr($new_cal_password, 0, 2));
          }
        }
        
        my $new_cal_id;
        
        if ($cal_valid == 1)
        {
          $new_cal_id = $max_new_cal_id + 1;
          
          $new_calendars{$new_cal_id}{id} = $new_cal_id;
          $new_calendars{$new_cal_id}{title} = $cal_title;
          $new_calendars{$new_cal_id}{details} = $cal_details;
          $new_calendars{$new_cal_id}{link} = $cal_link;
          $new_calendars{$new_cal_id}{list_background_calendars_together} = $list_background_calendars_together;
          $new_calendars{$new_cal_id}{calendar_events_color} = $calendar_events_color;
          $new_calendars{$new_cal_id}{background_events_fade_factor} = $background_events_fade_factor;
          $new_calendars{$new_cal_id}{background_events_color} = $background_events_color;
          $new_calendars{$new_cal_id}{default_number_of_months} = $default_number_of_months;
          $new_calendars{$new_cal_id}{max_number_of_months} = $max_number_of_months;
          $new_calendars{$new_cal_id}{gmtime_diff} = $gmtime_diff;
          $new_calendars{$new_cal_id}{date_format} = $date_format;
          $new_calendars{$new_cal_id}{week_start_day} = $week_start_day;
          $new_calendars{$new_cal_id}{info_window_size} = $info_window_size;
          $new_calendars{$new_cal_id}{custom_template} = $custom_template;
          $new_calendars{$new_cal_id}{custom_stylesheet} = $custom_stylesheet;
          $new_calendars{$new_cal_id}{password} = $input_password;
          $new_calendars{$new_cal_id}{update_timestamp} = $rightnow;
          $new_calendars{$new_cal_id}{allow_remote_calendar_requests} = $allow_remote_calendar_requests;
          $new_calendars{$new_cal_id}{remote_calendar_requests_require_password} = $remote_calendar_requests_require_password;
          $new_calendars{$new_cal_id}{remote_calendar_requests_password} = $remote_calendar_requests_password;
          
          # local background calendars            
          foreach $local_background_calendar (@local_background_calendars)
            {$new_calendars{$new_cal_id}{local_background_calendars}{$local_background_calendar} = 1;}
            
          # selectable calendars            
          foreach $selectable_calendar (@selectable_calendars)
            {$new_calendars{$new_cal_id}{selectable_calendars}{$selectable_calendar} = 1;}
        }  
          
        # check for refreshes!
        if ($cal_valid == 1)
        {
          if ($new_calendars{$new_cal_id}{title} eq $latest_new_calendar{title} &&
              $new_calendars{$new_cal_id}{details} eq $latest_new_calendar{details} &&
              $new_calendars{$new_cal_id}{link} eq $latest_new_calendar{link})
          {
            $cal_valid = 0;
            push @results_messages, $lang{update_cal_dup};
          }
        }
          
        if ($cal_valid == 1)  #all checks successful, add calendar!
        { 
          &add_new_calendar($new_cal_id);
          
          my $new_cal_details = &generate_cal_details($new_calendars{$new_cal_id});
          $new_cal_details =~ s/<a.+Delete this.+<\/a>//;
          $new_cal_details =~ s/Link directly.+<\/a>//s;

          if ($options{new_calendar_request_notify} ne "")
          {
            my $body = <<p1;
$lang{add_cal_email_notify1}
  
$new_cal_details  
  
<a href="$script_url/$name?active_tab=2&add_edit_cal_action=view_pending">$lang{add_cal_success3}</a>

p1
            &send_email($options{new_calendar_request_notify}, $options{reply_address}, $options{reply_address}, $lang{add_cal_email_notify2}, $body);
          }

          my $temp = $lang{add_cal_success1};  # add successful
          if ($add_edit_cal_action eq "edit")
            {$temp = $lang{add_cal_success4}}; # update successful
        
          $cal_add_results .= <<p1;
<div style="text-align:left;">
<p style="font-weight:bold;">
$temp
</p>

<div class="info_box">
$new_cal_details
</div>

<p style="margin-top:1em;">
$lang{add_cal_success2}
</p>

<ul>
<li><a href="$script_url/$name?active_tab=2&add_edit_cal_action=view_pending">$lang{add_cal_success3}</a>
</ul>
</div>
p1
          close FH;
        }
        else
        {
          push @results_messages, $lang{add_cal_fail1};
        }
      }
      close FH;
    }
    # properly format errors & warnings
    my $message_results="";
    foreach $results_message (@results_messages)
    {
      $results_message =~ s/(.*$lang{Warning})/<span class="warning">$1<\/span>/i;
      $results_message =~ s/(.*$lang{Error})/<span class="error">$1<\/span>/i;
      $message_results .= "<li>$results_message</li>\n";
    }
  
    $cal_add_results = "<ul style=\"font-size:small;\">$message_results</ul>$cal_add_results";
  }
    
  $return_text .=<<p1;
<div style="text-align:left;">
$cal_add_results
$cal_del_results
</div>
p1
  return $return_text;
} #********************end add_edit_calendars code*****************************


sub view_pending_calendars
{
  my $return_text = "";
  
  if ($q->param('approve_cal_button') eq "")  #view pending calendars main screen
  {    
    $cal_details ="";
    $shared_cal_select_size = scalar keys %calendars;

    $return_text.=<<p1;
<p class="cal_title">
$lang{view_pending_calendars1}
</p>
p1

       
    if (scalar keys %new_calendars == 0)
    {
      $return_text.=<<p1;
<p class="optional_field">
$lang{view_pending_calendars2}
</p>
p1
    }
    else
    {
      $return_text.=<<p1;
<form name="pending_calendars_form" action="">
<input type="hidden" name="active_tab" value="2">
<input type="hidden" name="add_edit_cal_action" value="view_pending">
p1
    
      foreach $new_cal_id (keys %new_calendars)
      {
        my $new_cal_details = &generate_cal_details($new_calendars{$new_cal_id});
        $new_cal_details =~ s/<a.+Delete this.+<\/a>//;
        $new_cal_details =~ s/Link directly.+<\/a>//s;
#Link directly to this calendar:<br/>
#<a href="$script_url/$name?cal_id=$calendar{id}">$script_url/$name?cal_id=$calendar{id}</a>    

        
      
        $return_text.=<<p1;
<div class="info_box" style="float:left;text-align:left;width:40%;margin:10px;clear:both;">
$new_cal_details
</div>
<div style="float:left;text-align:left;margin:10px;">
<br/>
<input type="radio" name="new_cal_$new_cal_id" value="approve"/><span class="optional_field">$lang{view_pending_calendars3}</span><br/><br/>
<input type="radio" name="new_cal_$new_cal_id" value="delete"/><span class="optional_field">$lang{view_pending_calendars4}</span><br/>
</div>
<br style="clear:both;"/>
p1
      }
      $return_text.=<<p1;
<div style="clear:both;"> 

<label for="main_password" class="optional_field">
$calendars{0}{title} Password:
</label>
<input type=password id="main_password" name = "main_password" size=10>
<br/>
<input type=submit name="approve_cal_button" value = "$lang{view_pending_calendars5}">
</form>
</div>

p1
    }
  }
  else  #view pending calendars approve/delete results screen
  {
    my @pending_calendars_to_delete;
    my @calendars_to_add;
    my @calendars_to_update;
    
    $cal_details ="";
    $shared_cal_select_size = scalar keys %calendars;

    $return_text.=<<p1;
<p class="cal_title">
$lang{view_pending_calendars6}
</p>
p1

    #check password
    $input_password = crypt($q->param('main_password'), 