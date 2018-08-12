from django.db import models


class Contributor(models.Model):
    username = models.CharField(max_length=200, unique=True)

    def __repr__(self):
        return f'<Contributor {self.username}>'

    def __str__(self):
        return f'Contributor {self.username}'


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __repr__(self):
        return f'<Tag {self.name}>'

    def __str__(self):
        return f'Tag {self.name}'


class Commit(models.Model):
    sha = models.CharField(max_length=100, unique=True)
    creation_date = models.DateTimeField(db_index=True)
    author = models.ForeignKey(Contributor, on_delete=models.CASCADE, db_index=True)
    message = models.TextField()
    merge = models.BooleanField()

    tags = models.ManyToManyField(Tag, db_index=True)

    def __repr__(self):
        return f'<Commit {self.sha}>'

    def __str__(self):
        return f'Commit {self.sha}'
