#!/bin/bash

MAPR_CLUSTERS_CONF=/opt/mapr/conf/mapr-clusters.conf
MAPR_SSL_KEYSTORE_PATH=/opt/mapr/conf/ssl_keystore
SECURE='false'
SRC_KEYSTORE=keystore.jks
DEST_KEYSTORE=keystore.p12
CERTIFCATE_PEM_FILE=cert.pem
SRC_STORE_PASSWD=mapr123
DEST_STORE_PASSWD=maprtech
OPENSSL_PKCS12_OUT=keystore.pem
OPENSSL_RSA_OUT=hue_private_keystore.pem
CERTIFICATEKEY=certificate

function find_cluster_name() {
if [[ -f $MAPR_CLUSTERS_CONF ]]; then
    LINE=$(head -n 1 $MAPR_CLUSTERS_CONF)
    echo "$(echo "$LINE"| awk '{print $1}')"
else echo ''
fi
}

function find_is_secure_enabled() {
if [[ -f $MAPR_CLUSTERS_CONF ]];then
    LINE=$(head -n 1 $MAPR_CLUSTERS_CONF)
    echo "$LINE"| awk '{print $2}'| awk -F'=' '{print $2}' | awk '{print tolower($0)}'
else echo 'false'
fi
}

SECURE=$(find_is_secure_enabled)

function input_certificat_key() {
read -p "[INPUT] Certificat key ["$CERTIFICATEKEY"]: " ANSWER
if [[ -n $ANSWER ]]; then
    CERTIFICATEKEY=$ANSWER
fi
}

function input_src_keysore() {
read -p "[INPUT] Source keystore ["$SRC_KEYSTORE"]: " ANSWER
if [[ -n $ANSWER ]]; then
    SRC_KEYSTORE=$ANSWER
fi
}

function input_dest_keysore() {
read -p "[INPUT] Destination keystore ["$DEST_KEYSTORE"]: " ANSWER
if [[ -n $ANSWER ]]; then
    DEST_KEYSTORE=$ANSWER
fi
}

function input_certificate_pem() {
read -p "[INPUT] Certificate pem file name ["$CERTIFCATE_PEM_FILE"]: " ANSWER
if [[ -n $ANSWER ]]; then
    CERTIFCATE_PEM_FILE=$ANSWER
fi
}

function input_dest_store_paswd() {
read -p "[INPUT] Destination store password ["$DEST_STORE_PASSWD"]: " ANSWER
if [[ -n $ANSWER ]]; then
    DEST_STORE_PASSWD=$ANSWER
fi
}

function input_dest_key_pass() {
read -p "[INPUT] Destination key password ["$DEST_KEY_PASS"]: " ANSWER
if [[ -n $ANSWER ]]; then
    DEST_KEY_PASS=$ANSWER
fi
}

function input_keystore_pass() {
read -p "[INPUT] Key store password ["$SRC_STORE_PASSWD"]: " ANSWER
if [[ -n $ANSWER ]]; then
    SRC_STORE_PASSWD=$ANSWER
fi
}

input_keystore_pass

if [[ $SECURE == 'false' ]]; then
    input_certificat_key
    input_src_keysore
    echo '[INFO] Generating keystore.jks containing private key...'
    keytool -genkeypair -alias $CERTIFICATEKEY -keyalg RSA -validity 7 -keystore $SRC_KEYSTORE -storepass $SRC_STORE_PASSWD -keypass $SRC_STORE_PASSWD
    if [[ $? -ne 0 ]]; then
    echo '[ERROR] No keystore.jks generated.'
    exit 0
fi
else
    echo '[INFO] Using existing ssl_keystore: '$MAPR_SSL_KEYSTORE_PATH
    CERTIFICATEKEY=$(find_cluster_name)
    SRC_KEYSTORE=$MAPR_SSL_KEYSTORE_PATH
fi


input_certificate_pem
echo '[INFO] Generating certificate from keystore...'
keytool -export -alias $CERTIFICATEKEY -keystore $SRC_KEYSTORE -rfc -file $CERTIFCATE_PEM_FILE -storepass $SRC_STORE_PASSWD

if [[ $? -ne 0 ]]; then
    echo '[ERROR] No certificate has been generated.'
    exit 0
fi

input_dest_keysore
input_dest_store_paswd

echo '[INFO] Importing the keystore from JKS to PKCS12...'
keytool -importkeystore -srckeystore $SRC_KEYSTORE -destkeystore $DEST_KEYSTORE -srcstoretype JKS -deststoretype PKCS12 -srcstorepass $SRC_STORE_PASSWD -deststorepass ${DEST_STORE_PASSWD} -srcalias $CERTIFICATEKEY -destalias $CERTIFICATEKEY -srckeypass $SRC_STORE_PASSWD -destkeypass ${DEST_STORE_PASSWD} -noprompt

if [[ $? -ne 0 ]]; then
    echo '[ERROR] No keystore has been imported.'
    exit 0
fi

echo '[INFO] Converting pkcs12 to pem using OpenSSL...'
openssl pkcs12 -in $DEST_KEYSTORE -out $OPENSSL_PKCS12_OUT -passin pass:${DEST_STORE_PASSWD} -passout pass:${DEST_STORE_PASSWD}

if [[ $? -ne 0 ]]; then
    echo '[ERROR] No pkcs12 has been converted.'
    exit 0
fi

echo '[INFO] Hiding the pass phrase so Python doesnt prompt for password while connecting to Hive...'
openssl rsa -in $OPENSSL_PKCS12_OUT -out $OPENSSL_RSA_OUT -passin pass:${DEST_STORE_PASSWD}

if [[ $? -ne 0 ]]; then
    echo '[ERROR] No rsa is used.'
    exit 0
fi

echo '[INFO] See output here: '$(readlink -e $OPENSSL_RSA_OUT)
echo '[INFO] Done.'
