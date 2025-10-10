<?php 	

$localhost = "cve-2022-30887-db";
$username = "root";
$password = "pharmacy123";
$dbname = "mayurik_pharmacy";
$store_url = "http://localhost/dawapharma/";
// db connection
$connect = new mysqli($localhost, $username, $password, $dbname);
// check connection
if($connect->connect_error) {
  die("Connection Failed : " . $connect->connect_error);
} else {
  // echo "Successfully connected";
}

?>