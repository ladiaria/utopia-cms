import os
import traceback
import json
import pytz
from django.db.models import Q
from dateutil import parser
from datetime import datetime
from tempfile import NamedTemporaryFile
from core.models import Article, Journalist, Edition, Section, ArticleRel, Publication
from core.utils import html_to_markdown
from .superdesk import SuperDeskService


class ImportService:

    def __init__(self):
        self.superdesk_service = SuperDeskService()

    def import_articles(self, selected_data, stored_data):
        """
        Import articles from SuperDesk based on given date
        """
        try:
            sp_articles = list()
            for a in stored_data:
                r_art = next((s for s in selected_data if a.get("sp_id") == s.get('art_id')), None)
                if r_art:
                    # add section data to the stored article data
                    a.update({'section': r_art.get('section_id') if r_art else ''})
                    sp_articles.append(a)
            sp_notes_ids = Article.objects.filter(~Q(sp_id=None), ~Q(sp_id='')).values_list('sp_id', flat=True)
            # loading all journalists in memory for prevent the call to the database for each archive
            journalists = list(Journalist.objects.filter(~Q(email=None), ~Q(email='')))  # exclude not email journalists
            # get data for article rel relationship
            for sp_art in sp_articles:
                # Build the article and call the SP API for get the user
                art_id = sp_art.get("sp_id")
                # fix the date for store it
                sp_art['date_created'] = datetime.strptime(sp_art['date_created'], "%d-%m-%Y")
                if art_id:
                    data_pub = sp_art.get('publication').copy()
                    section_art = sp_art.get('section')
                    sp_art.pop('publication')  # remove publication from the articles keys list
                    sp_art.pop('exists')  # remove exists from the articles keys list
                    sp_art.pop('section')  # remove exists from the articles keys list
                    # convert html body to markdown
                    sp_art['deck'] = html_to_markdown(sp_art['deck'])
                    sp_art['body'] = html_to_markdown(sp_art['body'])
                    # check if already exists
                    if str(art_id) in sp_notes_ids:
                        # TODO: check if it is necessary update the journalist author
                        sp_art.pop('authors')  # remove authors from the articles keys list not updates for authors
                        Article.objects.filter(sp_id=str(art_id)).update(**sp_art)
                    else:
                        # find journalist by email in sp articles authors list
                        journalists = [j for j in journalists
                                       if next((s for s in sp_art.get('authors') if j.email == s.get('email')), None)]
                        sp_art.pop('authors')  # remove authors from the articles keys list
                        new_art = Article.objects.create(**sp_art)
                        for journalist in journalists:
                            new_art.byline.add(journalist)  # add relationship journalist
                        # find publication
                        pub = Publication.objects.filter(slug=data_pub.get('code')).first()
                        # find edition
                        last_edition = Edition.objects.filter(publication=pub).first()
                        # find section
                        selected_section = None
                        if section_art:
                            selected_section = Section.objects.filter(id=section_art).first()
                        if not selected_section:
                            selected_section = Section.objects.filter(
                                publications=pub).first() or Section.objects.all().first()
                        # create article rel
                        if last_edition and selected_section:
                            art_rel = ArticleRel.objects.create(
                                article=new_art, edition=last_edition, section=selected_section)
                            new_art.main_section = art_rel
                        new_art.publication = pub
                        new_art.save()
        except Exception as ex:
            print(str(ex), traceback.format_exc())
            raise

    def get_sp_articles(self):
        """
        Get articles from SuperDesk based on submitted status
        """
        try:
            # selected_date = date_param if date_param else datetime.now() - timedelta(days=1)  # get yesterday
            result_list = list()
            missing_authors = False
            # do the login
            self.superdesk_service.login()
            sp_articles = self.superdesk_service.get_submitted_articles()
            sp_articles_no_image = self.superdesk_service.get_not_image_articles(sp_articles)
            sp_notes_ids = Article.objects.filter(~Q(sp_id=None), ~Q(sp_id='')).values('id', 'sp_id')
            sp_feed_users = self.superdesk_service.get_users()  # get all superdesk registered users once
            current_pubs = Publication.objects.all().values('name', 'slug')
            for sp_art in sp_articles_no_image:
                # Build the article and call the SP API for get the user
                art_id = sp_art.get("_id")
                if art_id:
                    utc = pytz.UTC
                    parsed_date = parser.parse(sp_art.get("firstcreated")).replace(tzinfo=utc).date()
                    args = {
                        'headline': sp_art.get("headline"),
                        'deck': sp_art.get("abstract"),
                        'body': sp_art.get("body_html", ''),
                        'sp_id': str(art_id),
                        'type': 'NE',
                        'exists': False,
                        'date_created':  parsed_date.strftime("%d-%m-%Y"),
                        'authors': [],
                        'publication': {'name': '', 'code': ''}
                    }
                    # find and set the publication if exists
                    if sp_art.get('subject'):
                        qcode = sp_art.get('subject')[0]['qcode']
                        pub = next((p for p in current_pubs if p['slug'] == qcode), None)
                        if pub:
                            args.update({
                                'publication': {
                                    'name': pub['name'],
                                    'code': pub['slug']
                                }
                            })
                    # create the new one
                    sp_complete_art = self.superdesk_service.get_archive(art_id)
                    if sp_complete_art:
                        # set up for existence of the current sp article in the cms
                        r_art = next((a for a in sp_notes_ids if a.get("sp_id") == art_id), None)
                        if r_art:
                            args.update({'exists': True, 'id': r_art.get('id')})

                        # get user author email from metadata and find the journalist by email
                        # For use metadata approach uncomment this line
                        # user_email = sp_complete_art.get('user_email')
                        # find user by byline from the API
                        if sp_complete_art.get('authors') and len(sp_complete_art['authors'][0]) > 0:
                            sp_user_ids = [u['parent'] for u in sp_complete_art['authors']]
                            sp_users = [u for u in sp_feed_users if u.get('_id') in sp_user_ids]

                            user_emails = [{'email': sp_user.get('email'), 'name': sp_user.get('display_name')}
                                           for sp_user in sp_users if sp_user.get('email')]
                            if user_emails:
                                args.update({'authors': user_emails})
                        # present the warning one time
                        if not missing_authors:
                            missing_authors = True
                    result_list.append(args)
            return result_list, missing_authors
        except Exception as ex:
            print(str(ex), traceback.format_exc())
            raise

    def store_temp_json(self, data):
        """
        Store temporary json file on file system
        """
        try:
            f = NamedTemporaryFile(delete=False)  # this keep the file on file system
            open(f.name, 'w').write(json.dumps(data))
            return f.name
        except Exception as e:
            print(str(e), traceback.format_exc())
            raise

    def read_temp_json(self, tmp_file):
        """
        Read temporary file stored on file system
        """
        try:
            # read the temp file and return it content
            with open(tmp_file, 'r') as f:
                content = json.loads(f.read())
            return content
        except Exception as e:
            print(str(e), traceback.format_exc())
            raise

    def remove_temp_json(self, tmp_file):
        """
        Remove temporary file from the file system
        """
        try:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
        except Exception as e:
            print(str(e), traceback.format_exc())
            raise
