<?php
    include("vpos_plugin.php");

    $params = json_decode(fgets(STDIN), true);

    $llaveVPOSCryptoPub = file_get_contents($params['crypto_pubkey']);

    $llaveComercioFirmaPriv = file_get_contents($params['sign_privkey']);

    $array_get['XMLREQ'] = "";
    $array_get['DIGITALSIGN'] = "";
    $array_get['SESSIONKEY'] = "";

    VPOSSend($params['array_send'], $array_get, $llaveVPOSCryptoPub,
        $llaveComercioFirmaPriv, $params['vector']);

    fwrite(STDOUT, json_encode($array_get));
?>