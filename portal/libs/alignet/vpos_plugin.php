<?php




	function createXMLPHP5($arreglo){



		$camposValidos_envio = array(

		'acquirerId',
		'commerceId',
		'purchaseCurrencyCode',
		'purchaseAmount',
		'purchaseOperationNumber',
		'billingAddress',
		'billingCity',
		'billingState',
		'billingCountry',
		'billingZIP',
		'billingPhone',
		'billingEMail',
		'billingFirstName',
		'billingLastName',
		'language',
		'commerceMallId',
		'terminalCode',
		'tipAmount',
		'HTTPSessionId',
		'shippingAddress',
		'shippingCity',
		'shippingState',
		'shippingCountry',
		'shippingZIP',
		'shippingPhone',
		'shippingEMail',
		'shippingFirstName',
		'shippingLastName',
		'reserved1',
		'reserved2',
		'reserved3',
		'reserved4',
		'reserved5',
		'reserved6',
		'reserved7',
		'reserved8',
		'reserved9',
		'reserved10',
		'reserved11',
		'reserved12',
		'reserved13',
		'reserved14',
		'reserved15',
		'reserved16',
		'reserved17',
		'reserved18',
		'reserved19',
		'reserved20',
		'reserved21',
		'reserved22',
		'reserved23',
		'reserved24',
		'reserved25',
		'reserved26',
		'reserved27',
		'reserved28',
		'reserved29',
		'reserved30',
		'reserved31',
		'reserved32',
		'reserved33',
		'reserved34',
		'reserved35',
		'reserved36',
		'reserved37',
		'reserved38',
		'reserved39',
		'reserved40'


		);



		$arrayTemp = array();
		$taxesName = array();
		$taxesAmount = array();




		$dom = new DOMDocument('1.0', 'iso-8859-1');



		$raiz = $dom->createElement('VPOSTransaction1.2');



		$dom->appendChild($raiz);



		foreach($arreglo as $key => $value){

			if(in_array($key,$camposValidos_envio)){

				$arrayTemp[$key] = $value;


			}
			else if(preg_match('tax_([0-9]{1}|[0-9]{2})_name',$key)){

				$keyam = preg_replace('(^tax_)|(_name$)','',$key);

				$taxesName[$keyam] = $value;

				//array_push($taxesName,array($keyam => $value));
			}else if(preg_match('tax_([0-9]{1}|[0-9]{2})_amount',$key)){

				$keyam = preg_replace('(^tax_)|(_amount$)','',$key);

				$taxesAmount[$keyam] = $value;

				//array_push($taxesAmount,array($keyam => $value));
			}else{

				die($key.' is not allowed in plugin');

			}

		}



		foreach($arrayTemp as $key => $value){
			$elem = new DOMElement($key,$value);
			$raiz -> appendChild($elem);
		}



		if(count($taxesName)>0){

			$elem = $raiz->appendChild(new DOMElement('taxes'));

			foreach($taxesName as $key => $value){
				$tax = $elem->appendChild(new DOMElement('Tax'));

				$tax->setAttributeNode(new DOMAttr('name',$value));
				$tax->setAttributeNode(new DOMAttr('amount',$taxesAmount[$key]));
			}

		}



		return $dom->saveXML();
	}


	function VPOSSend($arrayIn,&$arrayOut,$llavePublicaCifrado,$llavePrivadaFirma,$VI){



		$veractual = phpversion();



		if(version_compare($veractual,"5.0")<0){

			die('PHP version is '.$veractual.'and should be >=5.0');


		}

		$xmlSalida = createXMLPHP5($arrayIn);



		//Genera la firma Digital

		$firmaDigital = BASE64URL_digital_generate($xmlSalida,$llavePrivadaFirma);



		//Ya se genero el XML y se genera la llave de sesion
		$llavesesion = generateSessionKey();



		//Se cifra el XML con la llave generada
		$xmlCifrado = BASE64URL_symmetric_cipher($xmlSalida,$llavesesion,$VI);

		if(!$xmlCifrado) return null;

		//Se cifra la llave de sesion con la llave publica dada

		$llaveSesionCifrada = BASE64URLRSA_encrypt($llavesesion,$llavePublicaCifrado);

		if(!$llaveSesionCifrada) return null;


		if(!$firmaDigital) return null;

		$arrayOut['SESSIONKEY'] = $llaveSesionCifrada;
		$arrayOut['XMLREQ'] = $xmlCifrado;
		$arrayOut['DIGITALSIGN'] = $firmaDigital;

		return true;
	}

 	function VPOSResponse($arrayIn,&$arrayOut,$llavePublicaFirma,$llavePrivadaCifrado,$VI){

 		$veractual = phpversion();

		if(version_compare($veractual,"5.0")<0){

			trigger_error('La version de PHP es menor a la 5.0', E_USER_ERROR);
			return false;
		}

 		if($arrayIn['SESSIONKEY']==null
			|| $arrayIn['XMLRES']==null
			|| $arrayIn['DIGITALSIGN'] == null){
				return false;
		}

		$llavesesion = BASE64URLRSA_decrypt($arrayIn['SESSIONKEY'],$llavePrivadaCifrado);

		$xmlDecifrado = BASE64URL_symmetric_decipher($arrayIn['XMLRES'],$llavesesion,$VI);

		$validation = BASE64URL_digital_verify($xmlDecifrado,$arrayIn['DIGITALSIGN'],$llavePublicaFirma);

		if($validation){

			$arrayOut = parseXMLPHP5($xmlDecifrado);

			return true;
		}
		else{

			return false;
		}

 	}

	function is_num($s) {
		for ($i=0; $i<strlen($s); $i++) {
			if (($s[$i]<'0') or ($s[$i]>'9')) {return false;}
		}
		return true;
	}


 	function generateSessionKey(){

 		srand((double)microtime()*1000000);
 		return mcrypt_create_iv(16,MCRYPT_RAND);

 	}

	function BASE64URLRSA_encrypt ($valor,$publickey) {

 		if (!($pubres = openssl_pkey_get_public($publickey))){
 			die("Public key is not valid");

 		}

		$salida = "";

		$resp = openssl_public_encrypt($valor,$salida,$pubres,OPENSSL_PKCS1_PADDING);

		openssl_free_key($pubres);

		if($resp){
			$base64 = base64_encode($salida);
			$base64 = preg_replace('(/)','_',$base64);
			$base64 = preg_replace('(\+)','-',$base64);
			$base64 = preg_replace('(=)','.',$base64);

			return $base64;
		}
		else{

			die('RSA Ciphering could not be executed');

		}

	}

	function BASE64URLRSA_decrypt($valor,$privatekey){

 		 if (!($privres = openssl_pkey_get_private(array($privatekey,null))))
		 {
		 	die('Invalid private RSA key has been given');

		 }

		$salida = "";

		$pas = preg_replace('(_)','/',$valor);
		$pas = preg_replace('(-)','+',$pas);
		$pas = preg_replace('(\.)','=',$pas);

		$temp = base64_decode($pas);

		$resp = openssl_private_decrypt($temp,$salida,$privres,OPENSSL_PKCS1_PADDING);

		openssl_free_key($privres);

		if($resp){
			return $salida;
		}else{
			die('RSA deciphering was not succesful');

		}

	}

	function BASE64URL_symmetric_cipher($dato, $key, $vector)
	{

		$tamVI = strlen($vector);

		if($tamVI != 16){
			trigger_error('Initialization Vector must have 16 hexadecimal characters', E_USER_ERROR);

			return null;
		}

		if(strlen($key) != 16){
			trigger_error("Simetric Key doesn't have length of 16", E_USER_ERROR);

			return null;
		}

		$binvi = pack("H*", $vector);

		if($binvi == null){
			trigger_error("Initialization Vector is not valid, must contain only hexadecimal characters", E_USER_ERROR);
			return null;

		}

		$key .= substr($key,0,8); // agrega los primeros 8 bytes al final



		$text = $dato;
	  	$block = mcrypt_get_block_size('tripledes', 'cbc');
	   	$len = strlen($text);
	   	$padding = $block - ($len % $block);
	   	$text .= str_repeat(chr($padding),$padding);

		$crypttext = mcrypt_encrypt(MCRYPT_3DES, $key, $text, MCRYPT_MODE_CBC, $binvi);

		$crypttext = base64_encode($crypttext);
		$crypttext = preg_replace('(/)','_',$crypttext);
		$crypttext = preg_replace('(\+)','-',$crypttext);
		$crypttext = preg_replace('(=)','.',$crypttext);

		return $crypttext;
	}

	//-------------------------------------------------------------------------------------
	// Esta funcion se encarga de desencriptar los datos recibidos del MPI
	// Recibe como parametro el dato a desencriptar
	//-------------------------------------------------------------------------------------
	function BASE64URL_symmetric_decipher($dato, $key, $vector)
	{
		$tamVI = strlen($vector);

		if($tamVI != 16){
			trigger_error("Initialization Vector must have 16 hexadecimal characters", E_USER_ERROR);
			return null;
		}
		if(strlen($key) != 16){
			trigger_error("Simetric Key doesn't have length of 16", E_USER_ERROR);

			return null;
		}

		$binvi = pack("H*", $vector);

		if($binvi == null){
			trigger_error("Initialization Vector is not valid, must contain only hexadecimal characters", E_USER_ERROR);

			return null;

		}
		$key .= substr($key,0,8); // agrega los primeros 8 bytes al final

		$pas = preg_replace('(_)','/',$dato);
		$pas = preg_replace('(-)','+',$pas);
		$pas = preg_replace('(\.)','=',$pas);


		$crypttext = base64_decode($pas);

		$crypttext2 = mcrypt_decrypt(MCRYPT_3DES, $key, $crypttext, MCRYPT_MODE_CBC, $binvi);


		$block = mcrypt_get_block_size('tripledes', 'cbc');
		$packing = ord($crypttext2{strlen($crypttext2) - 1});
		if($packing and ($packing < $block))
		{
			for($P = strlen($crypttext2) - 1; $P >= strlen($crypttext2) - $packing; $P--)
			{
				if(ord($crypttext2{$P}) != $packing)
				{
					$packing = 0;
				}
			}
		}

		$crypttext2 = substr($crypttext2,0,strlen($crypttext2) - $packing);

		return $crypttext2;
	}

	//-------------------------------------------------------------------------------------
	// Esta funcion se encarga de generar una firma digital de $dato usando
	// la llave privada en $privatekey
	//-------------------------------------------------------------------------------------

 	function BASE64URL_digital_generate($dato, $privatekey)
 	{

 		$privres = openssl_pkey_get_private(array($privatekey,null));
 		 if (!$privres)
		 {
		 	die("Private key is not valid");

		 }


 		$firma = "";



 		$resp = openssl_sign($dato,$firma,$privres);

 		openssl_free_key($privres);

		if($resp){

			$base64 = base64_encode($firma);

			$crypttext = preg_replace('(/)' ,'_',$base64);
			$crypttext = preg_replace('(\+)','-',$crypttext);
			$crypttext = preg_replace('(=)' ,'.',$crypttext);

			//$urlencoded = urlencode($base64);
			return $crypttext;
		}
		else{
		die("RSA Signature was unsuccesful");
		}


 	}

 	function BASE64URL_digital_verify($dato,$firma, $publickey){

 		if (!($pubres = openssl_pkey_get_public($publickey))){
 			die("Public key is not valid");
 		}

 		$pas = preg_replace('(_)','/',$firma);
		$pas = preg_replace('(-)','+',$pas);
		$pas = preg_replace('(\.)','=',$pas);

 		$temp = base64_decode($pas);

 		$resp = openssl_verify($dato,$temp,$pubres);

 		openssl_free_key($pubres);

 		return $resp;
 	}


 	//

	function parseXMLPHP5($xml){

		$arregloSalida = array();

		$dom = new DOMDocument();
		$dom->loadXML($xml);

		$raiz = $dom->getElementsByTagName('VPOSTransaction1.2')->item(0);

		$nodoHijo = null;
		if($raiz->hasChildNodes()){
			$nodoHijo = $raiz->firstChild;
			$arregloSalida[$nodoHijo->nodeName] = $nodoHijo->nodeValue;
		}

		while (($nodoHijo=$nodoHijo->nextSibling)!=null) {
			$i = 1;
                        $nodoTax = "";
			if(strcmp($nodoHijo->nodeName,'taxes')==0){
				if($nodoHijo->hasChildNodes()){
					$nodoTax = $nodoHijo->firstChild;

					$arregloSalida['tax_'.$i.'_name'] = $nodoTax->getAttribute('name');
					$arregloSalida['tax_'.$i.'_amount'] = $nodoTax->getAttribute('amount');
					$i++;

				}

				while (($nodoTax)!=null) {
					$arregloSalida['tax_'.$i.'_name'] = $nodoTax->getAttribute('name');
					$arregloSalida['tax_'.$i.'_amount'] = $nodoTax->getAttribute('amount');
					$i++;
                                        $nodoTax = $nodoTax->nextSibling;
				}

			}else {
				$arregloSalida[$nodoHijo->nodeName] = $nodoHijo->nodeValue;
			}


		}

		return $arregloSalida;
	}

?>
