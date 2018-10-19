import requests
import asyncio
from django.db import models
from solo.models import SingletonModel
from collections import namedtuple


UserIssues = namedtuple('UserIssues', 'user issues')


def get_users_issues(redmine, sprint):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    users = redmine.get_users()
    tasks = [get_user_issues(redmine, sprint, user) for user in users]
    users_issues = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    loop.close()
    return users_issues


async def get_user_issues(redmine, sprint, user):
    issues = redmine.get_issues(user=user, sprint=sprint)
    tasks = [get_issue(redmine.url+'/issues/%i.json' % issue['id'], payload={'key': redmine.apikey}) for issue in issues]
    issues = await asyncio.gather(*tasks, return_exceptions=True)
    return UserIssues(user, IssueCollection(issues, sprint))


async def get_issues(tasks):
    issues = await asyncio.gather(*tasks, return_exceptions=True)
    return issues


async def get_issue(url, method='get', payload=None):
    methods = {'get': requests.get,
               'post': requests.post}
    if payload is None:
        payload = {}
    r = methods[method](url, params=payload)
    return r.json()['issue']


class Redmine(SingletonModel):
    url = models.URLField(verbose_name='Адрес портала')
    apikey = models.CharField(max_length=100, verbose_name='API ключ')

    def request(self, path, method='get', payload=None):
        methods = {'get': requests.get,
                   'post': requests.post}
        if payload is None:
            payload = {}
        payload['key'] = self.apikey
        r = methods[method](self.url + path, params=payload)
        return r.json()

    def get_users(self):
        response = self.request('/users.json')
        return [User(**user) for user in response['users'] if user['login'] != 'admin']

    def get_issues(self, user=None, sprint=None):
        params = {'limit': 100, 'offset': 0, 'status_id': '*', 'key': self.apikey}
        if user:
            params['assigned_to_id'] = user.id
        if sprint:
            params['cf_1'] = sprint.name
        response = self.request('/issues.json', payload=params)
        issues = response['issues']
        while response['offset']+response['limit'] < response['total_count']:
            params['offset'] += params['limit']
            response = self.request('/issues.json', payload=params)
            issues.append(response['issues'])
        return issues

    class Meta:
        verbose_name = 'Конфигурация Redmine'
        verbose_name_plural = 'Конфигурация Redmine'


class Sprint(models.Model):
    name = models.CharField(max_length=100)
    hours = models.FloatField(verbose_name='Кол-во часов')
    start = models.DateField(verbose_name='Дата начала')
    end = models.DateField(verbose_name='Дата завершения')

    class Meta:
        verbose_name = 'Спринт'
        verbose_name_plural = 'Спринты'


class User:
    _id = None
    login = None
    firstname = None
    lastname = None
    mail = None
    created_on = None
    last_login_on = None

    def __init__(self, id=None, login=None, firstname=None, lastname=None, mail=None, created_on=None,
                 last_login_on=None, *args, **kwargs):
        self._id = id
        self.login = login
        self.firstname = firstname
        self.lastname = lastname
        self.mail = mail
        self.created_on = created_on
        self.last_login_on = last_login_on

    @property
    def id(self):
        return self._id

    def __str__(self):
        if self.firstname and self.lastname:
            return '%s %s' % (self.lastname, self.firstname)
        return self.login


class Issue:
    pass


class IssueCollection:
    _issues = []
    _sprint = None
    _deviation = None
    _estimated_hours = None
    _spent_hours = None
    _left_hours = None
    _left_percent = None
    _spent_percent = None

    def __init__(self, issues, sprint):
        self._issues = issues
        self._sprint = sprint

    def __iter__(self):
        # статусы
        # 1 Новая
        # 2 В работе
        # 3 Выполнена
        # 5 Закрыта
        # 6 Отклонена
        # 7 Требует уточнения
        # 8 Прошла Code Review
        # 10 Приостановлена
        # 11 Возвращена в работу
        # 12 Требует уведомления заказчика
        order_statuses = {1: 3, 2: 1, 3: 10, 5: 15, 6: 20, 7: 5, 8: 10, 10: 3, 11: 2, 12: 10}
        return iter(sorted(self._issues, key=lambda issue: (order_statuses[issue['status']['id']], issue['priority']['id']*-1, issue['project']['name'], issue['subject'])))

    @property
    def spent_hours(self):
        if self._spent_hours is None:
            self._spent_hours = round(sum([issue.get('spent_hours', 0) for issue in self]), 2)
        return self._spent_hours

    @property
    def estimated_hours(self):
        if self._estimated_hours is None:
            hours = []
            for issue in self:
                estimated = issue.get('estimated_hours', 0)
                spent = issue.get('spent_hours', 0)
                complete_statuses = [3, 5, 6, 8]
                if issue['status']['id'] in complete_statuses:
                    hours.append(spent)
                else:
                    hours.append(estimated if estimated > spent else spent)
            self._estimated_hours = round(sum(hours), 2)
        return self._estimated_hours

    @property
    def left_hours(self):
        if self._left_hours is None:
            self._left_hours = round(self._sprint.hours - self.estimated_hours, 2)
        return self._left_hours

    @property
    def left_percent(self):
        if self._left_percent is None:
            self._left_percent = round((self.estimated_hours/(self._sprint.hours/100)))
        return self._left_percent

    @property
    def deviation(self):
        if self._deviation is None:
            hours = []
            for issue in self:
                estimated = issue.get('estimated_hours', 0)
                spent = issue.get('spent_hours', 0)
                if spent > estimated:
                    hours.append(spent - estimated)
            self._deviation = round(sum(hours), 2)
        return self._deviation

    @property
    def spent_percent(self):
        if self._spent_percent is None:
            estimated = self.estimated_hours
            spent = self.spent_hours
            if estimated == 0:
                if spent == 0:
                    return 0
                return 101
            self._spent_percent = round(spent/(estimated/100))
        return self._spent_percent
