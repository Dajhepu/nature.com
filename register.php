<?php
$email = $_POST['email'];
$psw = $_POST['psw'];
$pswrepeat = $_POST['pswrepeat'];


$conn = new mysqli('localhost','root','root','register');
if($conn->connect_error){
	die('Conection Failed : ' .$conn->connect_error);
}else{
	$stmt = $conn->prepare('insert into registretion(email,psw,pswrepeat)
		values(?, ?, ?)');
	$stmt->bind_param('sss', $email, $psw, $pswrepeat);
	$stmt->execute();
	echo "registration Successfully... ";
	$stmt->close();
	$conn->close();
}

?>