from csv import DictReader

from core.models import CategoryHome, CategoryHomeArticle


for home in DictReader(open('/tmp/core_home.csv'), delimiter='\t'):
    ch, created = CategoryHome.objects.get_or_create(category_id=home['category_id'])
    home_article, created = CategoryHomeArticle.objects.get_or_create(
        home=ch, article_id=home['cover_id'], position=1, fixed=int(home['fixed'])
    )

    for module in DictReader(open('/tmp/core_module.csv'), delimiter='\t'):
        if module['home_id'] == home['id']:
            for i in range(1, 10):
                aid = module['article_%d_id' % i]
                if aid != 'NULL':
                    home_article, created = CategoryHomeArticle.objects.get_or_create(
                        home=ch, article_id=aid, position=i + 1, fixed=int(module['article_%d_fixed' % i])
                    )
