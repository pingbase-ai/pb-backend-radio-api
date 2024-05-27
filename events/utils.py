from django.db.models import Prefetch, OuterRef, Subquery, Max
from home.models import EndUserSession


def optimize_event_queryset(queryset):
    """
    Optimizes the queryset for `Event` model to reduce the number of database queries
    when accessing related user data and their sessions.
    """
    last_session_subquery = (
        EndUserSession.objects.filter(end_user=OuterRef("pk"))
        .order_by("-modified_at")
        .values("last_session_active")[:1]
    )

    queryset = (
        queryset.select_related("src_user__end_user", "dest_user__end_user")
        .prefetch_related(
            Prefetch("src_user__end_user__sessions"),
            Prefetch("dest_user__end_user__sessions"),
        )
        .annotate(
            src_last_session=Subquery(last_session_subquery),
            dest_last_session=Subquery(last_session_subquery),
        )
    )

    return queryset
