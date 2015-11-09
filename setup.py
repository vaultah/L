import json
import sys
from setuptools import setup, Command
from pathlib import Path
import shutil
from string import Template
from pip.req import parse_requirements
from pip.download import PipSession
import time
import os
import signal
import subprocess

ROOT = Path(__file__).resolve().parent
CONFIG, NEW_CONFIG = ROOT / '_config', ROOT / 'L-config'
    
# Assuming these dir
NGINX_ROOT = Path('/etc') / 'nginx'
NGINX_AVAILABLE = NGINX_ROOT / 'sites-available'
NGINX_ENABLED = NGINX_ROOT / 'sites-enabled'

__version__ = '0.0.1'


class Prepare(Command):

    description = 'Prepare configuration files'
    user_options = []

    config = {
        'host': 'localhost',
        'media_domain': 'img',
        'smtp_host': 'localhost',
        'rev': ''
    }

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


    def json_conf(self):
        try:
            NEW_CONFIG.mkdir()
        except FileExistsError:
            pass
        with (NEW_CONFIG / 'L.json').open('w') as f:
            json.dump(self.config, f, indent=4, sort_keys=True)

 
    def run(self):
        self.json_conf()


class Deploy(Command):

    description = '"Install" the project'
    user_options = []
    config = Prepare.config

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def media_dirs(self):
        from app.consts import L_MEDIA_IMAGES
        try:
            L_MEDIA_IMAGES.mkdir(parents=True)
        except FileExistsError:
            pass

    def available_enabled(self):
        # Generate and safe
        names = {
            'nginx_main.conf': '{host}.conf'.format_map(self.config),
            'nginx_media.conf': '{media_domain}.{host}.conf'.format_map(self.config)
        }
        for old, new in names.items():
            tpl, rnd = CONFIG / old, NEW_CONFIG / new
            with tpl.open() as fin, rnd.open('w') as fout:
                # Kind of namespace
                prefixed = {'L_{}'.format(k): v for k, v in self.config.items()}
                print(Template(fin.read()).safe_substitute(prefixed), file=fout)
            # Move
            available = NGINX_AVAILABLE / new
            shutil.copyfile(str(rnd), str(available))
            # Link
            try:
                (NGINX_ENABLED / new).symlink_to(available)
            except FileExistsError:
                print('{}: the symlink is already there'.format(available))

    def run(self):
        from app import consts
        self.config['media_public'] = str(consts.L_MEDIA)
        self.config['main_public'] = str(consts.L_PUBLIC)
        with (NEW_CONFIG / 'L.json').open() as f:
            self.config.update(json.load(f))
        self.available_enabled()
        self.media_dirs()


class Run(Command):
    
    description = 'Run the project'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    # FIXME
    def run(self): 
        UWSGI_PROCESSES = 1
        LOGS = Path('/var/log')
        MONGOLOGS = LOGS / 'mongo'
        UWSGILOGS = LOGS / 'uwsgi'

        for p in (MONGOLOGS, UWSGILOGS):
            try:
                p.mkdir(parents=True)
            except FileExistsError:
                pass

        now = int(time.time())

        print('Rewinding', '{}'.format('-' * 50),
              sep='\n', end='\n\n')

        # TODO: Start WS server

        # MONGODB
        print('Starting the MongoDB:')
        mongo_log = MONGOLOGS / 'mongo-{}.log'.format(now)
        subprocess.call(['mongod', '--fork', '--logpath', str(mongo_log)])

        # UWSGI
        print('Starting UWSGI:')
        c = subprocess.Popen(['pidof', 'uwsgi'], stdout=subprocess.PIPE)
        pids, _ = c.communicate()

        if pids:
            print('Killing old uWSGI processes')
            for pid in pids.split():
                os.kill(int(pid), signal.SIGKILL)

        uwsgi_log = UWSGILOGS / '{0}-{1}.log'.format(now, '*')
        print('uWSGI Log mask: {}'.format(uwsgi_log))

        for x in range(1, UWSGI_PROCESSES + 1):
            sys.stdout.write('\r')
            sys.stdout.write('Starting {}/{} instance -> '.format(x, UWSGI_PROCESSES))

            subprocess.call(['uwsgi',   '--module', 'app.app',
                                        '--master',
                                        '--socket', '/tmp/uwsgi-{}.sock'.format(x), 
                                        '--harakiri', '30',
                                        '--listen', '1',
                                        '--enable-threads',
                                        '--memory-report',
                                        '--max-requests', '2000',
                                        '--reload-on-exception',
                                        '--daemonize', str(uwsgi_log).format(now, x)])
            sys.stdout.flush()

        print('Done.')

it = parse_requirements(str(ROOT / 'requirements.txt'),
                        session=PipSession())

setup(
    name='L',
    cmdclass={'prepare': Prepare, 'deploy': Deploy, 'run': Run},
    license='MIT',
    url='',
    version=__version__,
    install_requires=[str(ir.req) for ir in it],
)