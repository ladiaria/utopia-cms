#!/bin/bash
# O scriptcíleo do bacapi - la diaria - http://ladiaria.com/
# Distributed under the GNU/GPL license.
CONF_FILE="$0.conf"
# DIR=$(dirname $0)
# Expected environment variables from $CONF_FILE:
    # SOURCE_DIR
    # DEST_DIR
    # DB_USER
    # DB_NAME
    # DB_PASSWD
    # DB_TABLES -- Optional
if [ ! -e "$CONF_FILE" ]
then
    echo "Configuration file is missing"
    exit 1
else
    source $CONF_FILE
    if [ ! ${SOURCE_DIR} ]
    then
        echo "Source path is missing from conf file."
        exit 4
    else
        if [ ! -e "$SOURCE_DIR" ]
        then
            echo "Source path does not exist."
            exit 2
        fi
    fi
    if [ ! ${DEST_DIR} ]
    then
        echo "Destination path is missing from conf file."
        exit 4
    else
        if [ ! -e "$DEST_DIR" ]
        then
            echo "Destination path does not exist."
            exit 2
        fi
    fi
    if [ ! ${DB_USER} ]
    then
        echo "Database user is missing from conf file."
        exit 4
    fi
    if [ ! ${DB_NAME} ]
    then
        echo "Database name is missing from conf file."
        exit 4
    fi
    if [ ! ${DB_PASSWD} ]
    then
        echo "Database password is missing from conf file."
        exit 4
    fi
fi
TAR=`which tar`
DATE=`date +%Y%m%d`
SQL_DIR="$DEST_DIR/la_diaria-$DATE-sql"
cd $SOURCE_DIR/..
$TAR czf "$DEST_DIR/la_diaria-$DATE.tar.gz" "$(basename $SOURCE_DIR)"
mkdir $SQL_DIR 2>/dev/null
# dumps structure
mysqldump -u $DB_USER -p$DB_PASSWD --create-options -d $DB_NAME > $SQL_DIR/$DB_NAME.struct.sql
# dumps data
mysqldump -u $DB_USER -p$DB_PASSWD -c -n -t $DB_NAME > $SQL_DIR/$DB_NAME.data.sql
if [ "${DB_TABLES}" ]
then
    for TABLE in $DB_TABLES
    do
        # dumps structure
        mysqldump -u $DB_USER -p$DB_PASSWD --create-options -d $DB_NAME $TABLE > "$SQL_DIR/$DB_NAME-$TABLE.struct.sql"
        # dumps data
        mysqldump -u $DB_USER -p$DB_PASSWD -c -n -t $DB_NAME $TABLE > "$SQL_DIR/$DB_NAME-$TABLE.data.sql"
    done
fi
cd $DEST_DIR
$TAR czf "$DEST_DIR/la_diaria-$DATE-sql.tar.gz" "$(basename $SQL_DIR)"
rm -Rf "$SQL_DIR"
