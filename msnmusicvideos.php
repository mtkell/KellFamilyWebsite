<?php
require_once '/var/www/carp/carp.php';
// Add any desired configuration settings below this line using "CarpConf" and other functions


if (!($mi+=0)) $mi=15;
$hbw+=0;
$hbc=preg_replace("/[^a-zA-Z0-9. ]/",'',$hbc);
$hc=preg_replace("/[^a-zA-Z0-9. ]/",'',$hc);
$nw=preg_replace("/[^a-zA-Z0-9. ]/",'',$nw);

 CarpConf('outputformat',1);
  if (($doClass=strlen($hbc))||$hbw) {
   CarpConf('bilink','<div '.
      ($doClass?"class=\"$hbc\" ":'').
      ($hbw?"style=\"width:$hbw;":'').
      ($doClass?'':(';background:#cccccc;padding:2px;border-width:1px;'.
         'border-style:solid;border-color:#333333;')).
      ($hbw?'"':'').
   '>');
   CarpConf('ailink','</div>');
 }
 CarpConf('maxitems',$mi);
 if (strlen($hc)) CarpConf('ilinkclass',$hc);
 CarpConf('ilinktarget',$nw);
 
CarpConf('bilink','<h3>');
CarpConf('ailink','</h3>');

# CarpShow('/rss/headlines.rdf','');
# CarpCacheShow('http://www.geckotribe.com/press/rss/pr.rss');
CarpCacheShow('http://rss.video.msn.com/s/us/rss.aspx?t=hotVideo&c=topmusic&title=%20MSN%20Video%20-%20music&p=05','MSN_Music_Videos');
#CarpCacheShow('http://rss.cnn.com/rss/cnn_tech.rss','cnn_tech');
#CarpAggregate('cnn_headlines|cnn_tech');

?>
