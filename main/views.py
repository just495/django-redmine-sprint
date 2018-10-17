from django.shortcuts import render
from main.models import Redmine, Sprint, get_users_issues


def dashboard(request):
    redmine = Redmine.get_solo()
    sprint_id = request.GET.get('sprint')
    if sprint_id is None:
        sprint = Sprint.objects.order_by('name').last()
    else:
        sprint = Sprint.objects.get(pk=sprint_id)
    users_issues = get_users_issues(redmine, sprint)
    context = {
        'users_issues': sorted(users_issues, key=lambda user_issues: user_issues.issues.left_percent, reverse=True),
        'sprint': sprint,
        'sprints': Sprint.objects.order_by('-name')[:3],
        'redmine': redmine
    }
    return render(request, 'dashboard.html', context=context)
