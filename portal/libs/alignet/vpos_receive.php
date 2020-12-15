<?php
    include("vpos_plugin.php");
    $params = json_decode(fgets(STDIN), true);

    //Llave Firma Publica de Alignet
    $llaveVPOSFirmaPub = file_get_contents($params['sign_pubkey']);

    //Llave Crypto Privada del Comercio
    $llaveComercioCryptoPriv = file_get_contents($params['crypto_privkey']);

    $arrayOut = '';

    //Ejecución de Creación de Valores para la Solicitud de Interpretación de la Respuesta
    if(VPOSResponse($params['array_in'], $arrayOut, $llaveVPOSFirmaPub, $llaveComercioCryptoPriv,
            $params['vector'])){
        fwrite(STDOUT, json_encode($arrayOut));
    }else{
        fwrite(STDOUT, json_encode(array('error' => "Error durante el proceso de interpretación de la respuesta. "
            . "Verificar los componentes de seguridad: Vector Hexadecimal y Llaves.")));
    }
?>