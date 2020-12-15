import time

from locust import HttpUser, task, between

from local_settings import SSL_VERIFY, HTTP_BASIC_AUTH


class QuickstartUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def index_page(self):
        get_kwargs = {'verify': SSL_VERIFY}  # upd ssl verify from settings if it should be skipped

        # if basic auth is required
        if HTTP_BASIC_AUTH:
            get_kwargs['auth'] = HTTP_BASIC_AUTH

        self.client.get("/", **get_kwargs)

        # another page example
        # self.client.get("/world")

    """
    @task(3)
    def view_item(self):
        for item_id in range(10):
            self.client.get(f"/item?id={item_id}", name="/item")
            time.sleep(1)

    def on_start(self):
        self.client.post("/login", json={"username": "foo", "password":"bar"})
    """
