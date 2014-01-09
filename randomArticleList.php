<?php
/**
 * Created by PhpStorm.
 * User: jacek
 * Date: 27.11.13
 * Time: 14:26
 */


$link = mysql_connect( 'dw-s3', 'statsdb_ro' );
mysql_select_db('statsdb', $link);


$res = mysql_query( "SELECT wiki_id FROM dimension_top_wikis WHERE lang = 'en' ORDER BY rank LIMIT 5000", $link);

$wikiIds = [];

while ( $row = mysql_fetch_array($res) ) {
	$wikiIds[] = $row['wiki_id'];
}

shuffle($wikiIds);

$query = "SELECT dtw.url, dwa.title, dwa.wiki_id, dwa.article_id
	FROM dimension_wiki_articles dwa, dimension_top_wikis dtw
	WHERE dwa.wiki_id = dtw.wiki_id
	AND dwa.wiki_id IN (" .implode( ", ", $wikiIds ).")
	AND dwa.is_redirect = 0
	AND dwa.namespace_id = 0
	ORDER BY RAND()
	LIMIT 50
";

$res = mysql_query( $query, $link );
$resultArr = [];
while ( $result = mysql_fetch_array( $res ) ) {
	echo "http://" . $result['url'] . '/wiki/' . $result['title'] . "\n";
}

