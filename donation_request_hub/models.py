from django.db import models


class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(max_length=500)
    source = models.URLField(db_index=True, unique=True)

    def __str__(self):
        return self.title


class PostAlerts(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(max_length=500)
    source = models.URLField(db_index=True)

    def __str__(self):
        return self.title
