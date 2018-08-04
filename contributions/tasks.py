import datetime
import functools
import logging
import os
import re

import git
from celery import shared_task
from celery.decorators import periodic_task
from django.db import transaction

from .canonical_name import canonical_name

AUTHOR_REGEXP = re.compile(r"(?P<author>.*) \([0-9]+\)")
TAG_REGEXP = re.compile(r"^v[0-9\.]+$")

MISS_ISLINGTON_EMAIL = "31488909+miss-islington@users.noreply.github.com"
CHERRY_PICKED_REGEXP = re.compile(r"\(cherry picked from commit ([0-9a-f]{5,40})\)")

LOGGER = logging.getLogger(__name__)


@shared_task(rate_limit="1/m")
def setup_cpython_repo() -> None:
    LOGGER.info("Setting up CPython repository")
    if "cpython.git" in os.listdir("."):
        LOGGER.info("CPython directory already exists")
        return

    git.Repo.clone_from(
        "http://github.com/python/cpython/", to_path="./cpython.git", bare=True
    )

    logging.info(f"Finished setting up CPython Repo in %s", os.getcwd())


def update_cpython_repo(repo: git.Repo) -> None:
    LOGGER.info("Fetching latest changes")
    repo.remote().fetch(refspec="+refs/heads/*:refs/heads/*")
    LOGGER.info("Finished fetching changes")


@periodic_task(run_every=datetime.timedelta(minutes=30))
def update_database_objects() -> None:
    repo = git.Repo("cpython.git", odbt=git.GitCmdObjectDB)

    update_cpython_repo(repo)
    update_commits(repo)
    update_tags(repo)


def update_tags(repo: git.Repo) -> None:
    from .models import Commit, Tag

    tagrefs = [""]
    tagrefs += sorted(
        filter(lambda tag: TAG_REGEXP.match(tag), [tag.name for tag in repo.tags])
    )
    tagrefs += ["master"]
    n_current_tagrefs = Tag.objects.count()
    # Rebuild master if new tags
    if n_current_tagrefs + 1 != len(tagrefs):
        LOGGER.info("New tags received: deleting master")
        try:
            master = Tag.objects.get(name="master")
            master.delete()
        except Tag.DoesNotExist:
            pass

    for prev, tagref in zip(tagrefs, tagrefs[1:]):
        LOGGER.info("Getting range %s..%s", prev, tagref)
        with transaction.atomic():
            if prev:
                shas = {
                    commit.hexsha for commit in repo.iter_commits(f"{prev}..{tagref}")
                }
            else:
                first_sha = next(repo.iter_commits(max_parents=0)).hexsha
                shas = {
                    commit.hexsha
                    for commit in repo.iter_commits(f"{first_sha}..{tagref}")
                }
            tag, created = Tag.objects.get_or_create(
                name=tagref.replace("refs/tags/", "")
            )
            if created:
                tag.save()
            existing_shas = set(commit.sha for commit in tag.commit_set.all())
            missing_shas = set(shas) - existing_shas
            LOGGER.info(f"Adding {len(missing_shas)} commits to tag {tagref}")
            commits_to_insert = Commit.objects.filter(sha__in=missing_shas)
            tag.commit_set.add(*commits_to_insert)


@functools.lru_cache(maxsize=100)
def commit_canonical_author_name(repo, commit):
    author = commit.author
    if commit.author.email == MISS_ISLINGTON_EMAIL:
        author = get_original_commit_author(repo, commit)
    return canonical_name(name=author.name, email=author.email)


def get_original_commit_author(repo, commit):
    cherry_picked_shas = CHERRY_PICKED_REGEXP.findall(commit.message)
    if not cherry_picked_shas:
        return commit.author
    original_sha, *_ = cherry_picked_shas
    original_commit = repo.commit(original_sha)
    return original_commit.author


def update_commits(repo: git.Repo) -> None:
    from .models import Contributor, Commit

    all_commit_shas_in_repo = {commit.hexsha for commit in repo.iter_commits("--all")}
    all_commit_shas_in_db = set(commit.sha for commit in Commit.objects.all())
    missing_shas = set(all_commit_shas_in_repo) - all_commit_shas_in_db

    LOGGER.info("Adding %s commits to database", len(missing_shas))

    missing_commits = tuple(repo.commit(sha) for sha in missing_shas)
    authors_of_missing_commits = {
        commit_canonical_author_name(repo, commit) for commit in missing_commits
    }

    all_contributors_in_db = Contributor.objects.values_list("username")
    missing_contributors = set(authors_of_missing_commits) - set(all_contributors_in_db)

    LOGGER.info("Inserting contributors into database")

    Contributor.objects.bulk_create(
        [Contributor(username=username) for username in missing_contributors]
    )

    all_contributors_in_missing_commits = {
        contributor.username: contributor
        for contributor in Contributor.objects.filter(
            username__in=authors_of_missing_commits
        )
    }

    LOGGER.info("Inserting commits into database")

    Commit.objects.bulk_create(
        [
            Commit(
                sha=commit.hexsha,
                message=commit.message,
                author=all_contributors_in_missing_commits[
                    commit_canonical_author_name(repo, commit)
                ],
                creation_date=commit.committed_datetime,
                merge=bool(len(commit.parents) > 1),
            )
            for commit in missing_commits
        ]
    )

    LOGGER.info("Done")
