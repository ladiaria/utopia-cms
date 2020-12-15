-- Execute this queries before executing "20200716_set_main_section.py"

-- Replace subdomain by a starting /publication
UPDATE core_articleurlhistory
SET absolute_url=REGEXP_REPLACE(absolute_url, '^https:/(/\\w*)\.ladiaria.com.uy(.*)', '\\1\\2')
WHERE absolute_url RLIKE '^https://';

-- Remove base domain, not needed anymore
UPDATE core_articleurlhistory
SET absolute_url=REGEXP_REPLACE(absolute_url, '^https://ladiaria.com.uy(.*)', '\\1')
WHERE absolute_url RLIKE '^https://ladiaria.com.uy';

-- In local or test environments also run this using the corresponding hexxie.com, piques, etc
