from django.shortcuts import render


class ArticleAdmin(ModelAdmin):
    def get_urls(self):
        return [path('sp_import/', self.admin_site.admin_view(self.sp_import_view))] + super().get_urls()

    @never_cache
    def sp_import_view(self, request):
        """
        Handle the articles import process from SuperDesk to CMS ladiaria
        """
        from core.services.sp_import import ImportService
        try:
            service = ImportService()
            if 'import' in request.POST:
                # Performs the logic that store the data from request and stored into database
                tmp_file = request.POST.get('tmp_file')
                selected_items = request.POST.getlist('items[]')
                selected_articles = list()
                for s in selected_items:
                    section_input = 'selected-section-{}'.format(s)
                    if section_input in request.POST:
                        section_val = request.POST.get(section_input)
                        selected_articles.append({'art_id': s, 'section_id': section_val})
                    else:  # for articles previously imported
                        selected_articles.append({'art_id': s, 'section_id': ''})
                tmp_stored_data = service.read_temp_json(tmp_file)
                service.import_articles(selected_articles, tmp_stored_data)
                service.remove_temp_json(tmp_file)
            else:
                sp_articles, missing_authors = service.get_sp_articles()
                if len(sp_articles) > 0:
                    tmp_file = service.store_temp_json(sp_articles)
                    art_rel_form = ArticleRelAdminModelForm()
                    return render(request,
                                  'admin/core/article/sp_import_intermediate.html',
                                  context={'sp_articles': sp_articles,
                                           'tmp_file': tmp_file,
                                           'art_rel_form': art_rel_form,
                                           'debug': settings.DEBUG,
                                           })
                self.message_user(request, "No se encontraron artículos para importar", level=messages.WARNING)
        except Exception as e:
            msg = "Error al importar artículos desde SuperDesk"
            if settings.DEBUG:
                print("DEBUG: " + msg + str(e) + " : " + traceback.format_exc())
            self.message_user(request, msg, level=messages.ERROR)
        return HttpResponseRedirect("/admin/core/article/")
