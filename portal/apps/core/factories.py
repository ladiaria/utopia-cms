from django.contrib.auth import get_user_model

from factory.django import DjangoModelFactory
from factory import Sequence, Faker
from .models import Publication

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = Sequence(lambda n: f"user_03{n}@example.com")
    first_name = Sequence(lambda n: f"User 03{n}")
    username = Sequence(lambda n: f"username03{n}")
    last_name = Sequence(lambda n: f"Last Name 03{n}")


class PublicationFactory(DjangoModelFactory):
    class Meta:
        model = Publication

    name = Sequence(lambda n: f"Nombre{n}")
    twitter_username = Sequence(lambda n: f"Twit_user{n}")
    description = Faker('text')
    slug = "default"
    headline = Sequence(lambda n: f"headline{n}")

    weight = Sequence(lambda n: f"{n}")
    public = True
    has_newsletter = False
    newsletter_name = Sequence(lambda n: f"newsletter_name{n}")
    newsletter_tagline = Sequence(lambda n: f"newsletter_tagline{n}")
    newsletter_periodicity = Sequence(lambda n: f"newsletter_periodicity{n}")
    newsletter_header_color = '#262626'
    newsletter_campaign = Sequence(lambda n: f"newsletter_campaign{n}")
    newsletter_automatic_subject = True
    newsletter_subject = Sequence(lambda n: f"subject{n}")
    subscribe_box_question = Sequence(lambda n: f"subscribe_box_question{n}")
    subscribe_box_nl_subscribe_auth = Sequence(lambda n: f"subscribe_box_nl_subscribe_auth{n}")
    subscribe_box_nl_subscribe_anon = Sequence(lambda n: f"subscribe_box_nl_subscribe_anon{n}")
    image = None
    full_width_cover_image = None
    is_emergente = False
    new_pill = False
    icon = None
    icon_png = None
    icon_png_16 = None
    icon_png_32 = None
    apple_touch_icon_180 = None
    apple_touch_icon_192 = None
    apple_touch_icon_512 = None
    open_graph_image = None
    open_graph_image_width = Sequence(lambda n: n)
    open_graph_image_height = Sequence(lambda n: n)
    publisher_logo = None
    publisher_logo_width = None
    publisher_logo_height = None
