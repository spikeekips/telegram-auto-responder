# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='telegram-auto-responder',
    version='0.1',
    url='https://github.com/spikeekips/telegram-auto-responder',
    packages=('telegram_auto_responder',),
    package_dir={'': 'src'},
    author='Spike^ekipS',
    author_email='spikeekips@gmail.org',
    install_requires=(
        'DictObject',
        'luckydonald-utils',
        'pytg',
    ),
    scripts=['scripts/telegram-auto-responder'],
    zip_safe=False,
)
