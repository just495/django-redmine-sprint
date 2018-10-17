from django.shortcuts import render
from main.models import Redmine, Sprint
from collections import namedtuple


def dashboard(request):
    redmine = Redmine.get_solo()
    users = redmine.get_users()
    # получаем спринт
    sprint_id = request.GET.get('sprint')
    if sprint_id is None:
        sprint = Sprint.objects.order_by('name').last()
    else:
        sprint = Sprint.objects.get(pk=sprint_id)
    UserIssues = namedtuple('UserIssues', 'user issues')
    users_issues = [UserIssues(user, redmine.get_issues(user, sprint)) for user in users]
    context = {
        'users_issues': sorted(users_issues, key=lambda user_issues: user_issues.issues.left_percent, reverse=True),
        'sprint': sprint,
        'sprints': Sprint.objects.order_by('-name')[:3],
        'redmine': redmine
    }
    return render(request, 'dashboard.html', context=context)
