This was a work-in-progress (working) and then abandoned feature, to import articles from Superdesk, we are now
changing the strategy to export from superdesk and make API entry points in utopia CMS to consume that export.

Archived changes in files / directories:

* portal/apps/core/admin.py: admin.py
* portal/apps/core/services: services
* portal/apps/core/utils.py: utils.py
* portal/requirements.txt: `markdownify` removed
* portal/templates/admin/core/article/change_list.html: change_list.html
* portal/templates/admin/core/article/sp_import_intermediate.html: sp_import_intermediate.html
