import datetime

import django_filters
from django.http import HttpResponse, Http404
from django.template import loader
from django.db.models import Count, Q
from django_filters.views import FilterView
from django_filters.widgets import RangeWidget

from .models import Contributor, Tag, Commit

from django_tables2 import RequestConfig, tables, SingleTableMixin
from django_tables2.columns import TemplateColumn, LinkColumn
from django_tables2.utils import A


def all_time(request):
    valid_commits = Count("commit", filter=Q(commit__merge=False))
    all_contributors = Contributor.objects.annotate(
        number_of_commits=valid_commits
    ).order_by("-number_of_commits")
    template = loader.get_template("contributions/all_time.html")
    context = {"contributors": all_contributors}
    return HttpResponse(template.render(context, request))


class CommitFilter(django_filters.FilterSet):
    creation_date = django_filters.DateFromToRangeFilter(
        widget=RangeWidget(attrs={"class": "datepicker_from"})
    )

    class Meta:
        model = Commit
        fields = {"sha": ["icontains"]}


class CommitTable(tables.Table):
    sha = TemplateColumn(
        '<a href="https://github.com/python/cpython/commit/{{record.sha}}">{{record.sha}}</a>'
    )

    class Meta:
        model = Commit

        fields = ["sha", "creation_date", "message"]
        attrs = {"class": "responsive-table striped"}


class CommitTableWithAuthor(CommitTable):
    author = LinkColumn(
        "contributor_commits",
        text=lambda record: record.author.username,
        args=[A("author.id")],
    )

    class Meta:
        model = Commit

        fields = ["sha", "author", "creation_date", "message"]
        attrs = {"class": "responsive-table striped"}


class FilterCommitListView(SingleTableMixin, FilterView):
    table_class = CommitTable
    model = Commit

    filterset_class = CommitFilter

    def get_table_kwargs(self):
        return {"template_name": "django_tables2/bootstrap.html"}

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        if kwargs["data"] is None:
            kwargs["data"] = {}
        return kwargs


class ContributorCommitsView(FilterCommitListView):
    template_name = "contributions/contributor.html"
    paginate_by = 20

    def get_queryset(self):
        contributor = Contributor.objects.get(id=self.kwargs["id_"])
        commits = contributor.commit_set.filter(merge=False).order_by("-creation_date")
        return commits

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contributor = Contributor.objects.get(id=self.kwargs["id_"])
        context["contributor"] = contributor.username
        return context


class CommitsSinceListView(FilterCommitListView):
    table_class = CommitTableWithAuthor
    template_name = "contributions/commits_since.html"
    paginate_by = 100

    def _target_date(self):
        from_date = datetime.datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return from_date - datetime.timedelta(days=int(self.kwargs["days"]))

    def get_queryset(self):
        if self.kwargs["days"] > 31:
            raise Http404
        commits = Commit.objects.filter(creation_date__gt=self._target_date()).order_by(
            "-creation_date"
        )
        return commits

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["from_date"] = self._target_date().date()
        return context


def tag_contributors(request, tag):
    tag = Tag.objects.get(name=tag)
    author_ids = tag.commit_set.values_list("author__id", flat=True).distinct()
    authors = Contributor.objects.filter(id__in=author_ids).order_by("username")
    template = loader.get_template("contributions/contributors.html")
    context = {"contributors": authors}
    return HttpResponse(template.render(context, request))


def index(request):
    all_tags = (
        Tag.objects.filter(name__startswith="v")
            .order_by("-name")
            .values_list("name", flat=True)
    )
    template = loader.get_template("contributions/index.html")
    context = {"tags": ["master"] + list(all_tags)}
    return HttpResponse(template.render(context, request))
