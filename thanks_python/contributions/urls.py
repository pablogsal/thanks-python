from django.conf.urls import url
from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("all_time", views.all_time, name="all_time"),
    path("tag/<str:tag>", views.tag_contributors, name="tag_contributors"),
    path(
        "since/<int:days>", views.CommitsSinceListView.as_view(), name="commits_since"
    ),
    path(
        "contributor/<str:id_>",
        views.ContributorCommitsView.as_view(),
        name="contributor_commits",
    ),
]
