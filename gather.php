<?php
/*
 * Usage: php gather.php "http://wikia.com/wiki/article_title"
 */

$url = $argv[1];

$urlArr = explode("/wiki/", $url);
$urlBase = $urlArr[0] . "/";
$articleTitle = $urlArr[1];

$jsonOut = [];


/*
 * 	Inbound links
 */
$whatLinksHereUrl = "index.php?title=Special%3AWhatLinksHere&target=" . $articleTitle ."&limit=500";
$content = file_get_contents( $urlBase . $whatLinksHereUrl );
$linksCnt = 0;
$links = [];
preg_match_all('/<ul id="mw-whatlinkshere-list">(.*?)<\/ul>/ims', $content, $links);
if ( isset($links[1]) && !empty($links[1][0])) {
	$links = explode("<li>", $links[1][0] );
	$linksCnt = count( $links );
}
$jsonOut['inbound_links'] = $linksCnt;

/*
 * 	Outbound links
 */
$content = file_get_contents( $urlBase . "index.php?title=" . $articleTitle . "&action=render");
$outboundCnt = 0;
$outboundCnt = substr_count( $content, 'href="'.$urlBase );
$outboundCnt -= substr_count( $content, 'href="'.$urlBase."index.php" );

$jsonOut['outbound_links'] = $outboundCnt;




$out = [];
foreach ( $jsonOut as $key => $value ) {
	$out[] = '"'.$key.'":"'.$value.'"';
}
echo "{" . implode(",", $out) . "}";