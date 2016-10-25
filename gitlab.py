
import json
import hmac, hashlib
import threading
import http, http.server
from halibot import HalModule, Context, Message

def make_issues_report(event, payload):
	title = payload['object_attributes']['title']
	user = payload['user']['name']
	repo = payload['project']['name']

	if payload['action'] == 'opened':
		return 'New issue "{}" opened by {} in {}.'.format(title, user, repo)

	if payload['action'] == 'reopened':
		return 'Issue "{}" reopened by {} in {}.'.format(title, user, repo)

	if payload['action'] == 'closed':
		return 'Issue "{}" closed by {} in {}.'.format(title, user, repo)

	return None

def make_mr_report(event, action, payload):
	title = payload['object_attributes']['title']
	user = payload['user']['name']
	repo = payload['project']['name']

	if action == 'opened':
		return 'Pull request "{}" opened by {} in {}.'.format(title, user, repo)

	if action == 'reopened':
		return 'Pull request "{}" reopened by {} in {}.'.format(title, user, repo)

	if action == 'closed':
		merged = '' if payload['merge_request']['merged'] else 'not '
		return 'Pull request "{}" closed and {}merged by {} in {}.'.format(title, merged, user, repo)

	return None

def make_report(event, action, payload):
	fun = {
		'issues': make_issues_report,
		'merge_request': make_mr_report,
	}.get(event, None)
	
	if fun == None:
		return None

	return fun(event, action, payload)

class GitlabHookHandler(http.server.BaseHTTPRequestHandler):

	def do_POST(self):
		module = self.server.module
		config = module.config

		# filter out non-gitlab events
		if not 'X-Gitlab-Event' in self.headers:
			# Ignore and timeout
			module.log.info('Received something that is not a gitlab event, ignoring.')
			return
	
		length = int(self.headers['Content-Length'])
		data = self.rfile.read(length)

		if 'secret' in config:
			if config['secret'] != self.headers['X-Hub-Signature']:
				module.log.warning('Wrong secret key!')
				return

		# TODO read charset from header
		payload = json.loads(data.decode('utf-8'))

		event = payload['object_kind']
		action = payload['object_attributes']['state']

		module.log.debug('Received {} {} event.'.format(event, action))
		
		# ignore events we didn't ask for
		events = module.events
		if event in events and action in events[event]:
			report = make_report(event, action, payload)

			# Ignore events we don't know how to handle
			if report != None:
				msg = Message(body=report, author='halibot')
				module.log.debug('Reporting event to ' + config['dest'])
				module.send_to(msg, [ config['dest'] ])
			else:
				module.log.warning('Could not form report for "{} {}"'.format(event, action))

		self.send_response(204)
		self.end_headers()

class Gitlab(HalModule):

	options = {
		'secret': {
			'type'   : 'string',
			'prompt' : 'Shared secret',
		},
		'dest': {
			'type'   : 'string',
			'prompt' : 'Destination',
		},
		'port': {
			'type'   : 'int',
			'prompt' : 'Port to listen on',
			'default': 9000,
		},
	}

	# Override the configure method so we can do more complicated configuration prompts
	@classmethod
	def configure(cls, config):
		(name, config) = super(Gitlab, Gitlab).configure(config)

		def promptYn(prompt):
			yn = input(prompt + '? [Y/n] ')
			if len(yn) < 1: return True
			return yn[0].upper() == 'Y'

		issues = []
		mrs = []

		if promptYn('List for opened issues'):   issues.append('opened')
		if promptYn('List for reopened issues'): issues.append('reopened')
		if promptYn('List for closed issues'):   issues.append('closed')
		if promptYn('List for opened merge requests'):   mrs.append('opened')
		if promptYn('List for reopened merge requests'): mrs.append('reopened')
		if promptYn('List for closed merge requests'):   mrs.append('closed')

		config['events'] = {
			'issues': issues,
			'merge_request': mrs,
		}

		return (name, config)
		

	def init(self):
		self.events = self.config.get('events', {})

		addr = ('', self.config.get('port', 9000))
		self.server = http.server.HTTPServer(addr, GitlabHookHandler)
		self.server.module = self
		self.thread = threading.Thread(target=self.server.serve_forever)
		self.thread.start()

	def shutdown(self):
		self.server.shutdown()
		self.thread.join()

