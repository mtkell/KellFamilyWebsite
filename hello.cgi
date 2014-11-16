#!/usr/bin/perl

#hello: a simple Perl CGI Example

#Note that we output two carriage returns after the 
#content tpe. This is very important as it marks
#the end of the CGI "header" and the beginning of
#the document to be sent to the browser.

print "Content-type: text/html\n\n";
# Output a proper HTML document, with <head>
# and <body> tags. */

print "<head>\n";
print "<title>Hello World</title>\n";
print "</head>\n";
print "<body>\n";
print "<h1>Hello, World</h1>\n";
print "</body>;
