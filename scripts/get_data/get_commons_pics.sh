#!/bin/bash
# author: Nastasia Vanderperren (meemoo)

CSV=$1
OUTPUT_FOLDER=$2

tail -n +2 ${CSV} | \
while IFS="," read -r qid name category
do
	if [[ -n $category ]]
	then

		echo "[INFO] Searching for images of $name"

		folder="${OUTPUT_FOLDER}/${qid}"
		WIKI_URL="https://commons.wikimedia.org/wiki/Category:${category}"
		#WIKI_URL=${WIKI_URL// /_}
		echo $WIKI_URL
		# Download Image pages
		echo "[INFO] Downloading image Pages of $name"
		wget -q -r -l 1 -e robots=off -w 1 -nc "${WIKI_URL}"

		# Extract Image Links
		echo "[INFO] Extracting image links"
		WIKI_LINKS=`grep fullImageLink commons.wikimedia.org/wiki/File\:* | sed 's/^.*a href="//'| sed 's/".*$//'`

		if [[ -n $WIKI_LINKS ]]
		then
			echo $WIKI_LINKS
			echo "Downloading Images of $WIKI_URL"
			wget -nc -w 1 -e robots=off -P "${folder}" ${WIKI_LINKS}
			echo "[INFO] Files saved in ${folder}"
		else
			echo "[INFO] Commons page of $name has no images"
		fi

		echo "Cleaning up temp files"
		rm -rf commons.wikimedia.org/
		echo -e "Done\n"

	fi

done