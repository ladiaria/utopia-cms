from builtins import object
import inspect

from django.conf import settings
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from core.models import Article


@registry.register_document
class ArticleDocument(Document):
    """
    TODO: the method unformatted_body is also filled with related content (recuadros) if you change only these
          objects the signal to reindex is not executed.
          Try to fix this (ModelAdmin.save_related can be the right place to trigger the signal or whatever needed)
    """
    # target fields (Article methods) to search, TODO: if only used here, can be better to use "prepare_*"
    unformatted_headline = fields.TextField(attr="unformatted_headline")
    unformatted_lead = fields.TextField(attr="unformatted_lead")
    unformatted_deck = fields.TextField(attr="unformatted_deck")
    unformatted_body = fields.TextField(attr="unformatted_body")
    # other needed fields (Article methods) to render the results
    get_absolute_url = fields.TextField(attr="get_absolute_url")
    get_type_display = fields.TextField(attr="get_type_display")
    as_search_result = fields.TextField(attr="as_search_result")
    # section is also needed to render the results
    section = fields.TextField()

    def update(self, instance, refresh=None, action="index", **kwargs):
        # use stack info to avoid call to parent update if it came from a reversion-show-revision because they do
        # call save also when you're only viewing the form. Note that you must left unchanged (calling father)
        # when a revision is selected and confirmed to be reverted to it.
        # Against with we can imagine, "revert" is called only from this "revision view only" and not when a revert is
        # confirmed, then when "revert" is in the stack, we'll not call super.update.
        # To add more robustness, the whole call pattern to avoid update can be matched, when I wrote this, the pattern
        # was: revert, _safe_revert, revert, _revision_revisionform_view, revision_view, revision_view.
        for frame in inspect.stack():
            if frame.function == "revert":
                return
        return super().update(instance, refresh, action, **kwargs)

    def prepare_section(self, instance):
        return str(instance.section) if instance.section else ''

    def get_queryset(self):
        """ Useful in development, for example to reduce the number of articles to index by settings """
        qs = super(ArticleDocument, self).get_queryset()
        filter_kwargs = getattr(settings, "SEARCH_ELASTIC_ARTICLES_INDEX_FILTER_KWARGS", None)
        return qs.filter(**filter_kwargs) if filter_kwargs else qs

    class Index(object):
        # Name of the Elasticsearch index (TODO: use a better default name, for example "utopiacms_core_article")
        name = getattr(settings, "SEARCH_ELASTIC_ARTICLES_INDEX_NAME", 'articles')
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    class Django(object):
        model = Article  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = [
            # fields needed to filter the results
            'is_published',
            'date_published',
            # fields needed to render the results
            'headline',
            'type',
        ]

        # To ignore auto updating of Elasticsearch index when a model is saved or deleted, use:
        # ignore_signals = True

        # To don't perform an index refresh after every update (overrides global setting), use:
        # auto_refresh = False

        # To paginate the django queryset used to populate the index with the specified size
        # (by default it uses the database driver's default setting), use this example line:
        # queryset_pagination = 5000
