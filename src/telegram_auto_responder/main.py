# -*- coding: utf-8 -*-

import datetime
import logging
import os
import pprint  # noqa
import string
import threading
import time

from pytg.utils import coroutine
from pytg.receiver import Receiver
from pytg.sender import Sender

from storage import Storage


MESSAGES = (
    'new',
    'idle',
)


TB_TG_HOST = os.environ.get('TB_TG_HOST', 'localhost')  # telegram cli host
TB_TG_PORT = int(os.environ.get('TB_TG_PORT', 4458))         # telegram cli port
TB_LOGLEVEL = getattr(logging, os.environ.get('TB_LOGLEVEL', '').upper(), 'INFO')
TB_INTERVAL_RESPONSE_IDLE_DIALOG = int(os.environ.get('TB_INTERVAL_RESPONSE_IDLE_DIALOG', 3 * 60))
TB_UPDATE_DIALOG_LIST_INTERVAL = int(os.environ.get('TB_UPDATE_DIALOG_LIST_INTERVAL', 5))
TB_UPDATE_CONTACTS_LIST_INTERVAL = int(os.environ.get('TB_UPDATE_CONTACTS_LIST_INTERVAL', 9))
_TB_FORWARD_USERS = filter(bool, map(string.strip, os.environ.get('TB_FORWARD_USERS', '').split(',')))  # the target users fo rforwarding messages
_TB_FORWARD_USERS = map(lambda x: x.decode('utf-8'), _TB_FORWARD_USERS)
TB_MESSAGES_DIRECTORY = os.environ.get('TB_MESSAGES_DIRECTORY', None)

log_format = logging.Formatter('[%(levelname)5s] %(asctime)s: %(msg)s (%(module)s.%(funcName)s:%(lineno)d)')
log = logging.getLogger(__name__)
log.setLevel(TB_LOGLEVEL)
st = logging.StreamHandler()
st.setFormatter(log_format)
log.addHandler(st)


STORAGE = Storage(os.path.join(os.environ.get('HOME'), '.telegram-cli'))
RECEIVER = SENDER = None

DATA = dict()

if STORAGE.get('f', None) is None:
    STORAGE.set('f', dict())

if STORAGE.get('d', None) is None:
    STORAGE.set('d', dict())


def connect():
    global RECEIVER, SENDER

    log.debug('> trying to connect: %s:%s' % (TB_TG_HOST, TB_TG_PORT))
    RECEIVER = Receiver(host=TB_TG_HOST, port=TB_TG_PORT)
    SENDER = Sender(host=TB_TG_HOST, port=TB_TG_PORT)

    RECEIVER.start()
    log.debug('< connected')

    return


def is_forward_user(o):
    if o.get('username') in _TB_FORWARD_USERS:
        return True

    if o.get('print_name') in _TB_FORWARD_USERS:
        return True

    if o.get('id') in _TB_FORWARD_USERS:
        return True

    if o.get('phone') in _TB_FORWARD_USERS:
        return True

    return False


def _update_contact_list():
    log.debug('> trying to update contacts list')
    if 'contacts' not in DATA:
        DATA['contacts'] = list()

    try:
        l = SENDER.contacts_list()
    except TypeError:
        return

    DATA['contacts'] = l

    found_forward_user = filter(is_forward_user, DATA['contacts'])

    tb_forward_users = STORAGE.get('f', dict())
    for k, v in tb_forward_users.items():
        if v.get('_type') not in ('contact',):
            continue

        if True not in filter(lambda x: k == x.get('id'), found_forward_user):
            del tb_forward_users[k]

    for i in found_forward_user:
        if i.get('id') not in tb_forward_users:
            i['_type'] = 'contact'
            tb_forward_users[i.get('id')] = i

    log.debug('< updated contacts list')

    STORAGE.set('f', tb_forward_users)
    log.debug('< forwarded users: %s' % STORAGE.get('f'))

    return


def update_contact_list():
    log.debug('> trying to update contacts list')
    while True:
        try:
            _update_contact_list()
        except TypeError:
            pass

        time.sleep(TB_UPDATE_CONTACTS_LIST_INTERVAL)

    return


def _update_dialog_list():
    log.debug('> trying to update dialog list')

    dialogs = dict()

    found = list()
    found_forward_user = list()
    for i in SENDER.dialog_list():
        if is_forward_user(i):
            found_forward_user.append(i)

        if i.get('type') not in ('user',):
            continue

        p = i.get('phone')
        found.append(p)

        if p not in dialogs:
            dialogs[p] = i

    tb_forward_users = STORAGE.get('f', dict())
    for k, v in tb_forward_users.items():
        if v.get('_type') not in ('dialog',):
            continue

        if True not in filter(lambda x: k == x.get('id'), found_forward_user):
            del tb_forward_users[k]

    for i in found_forward_user:
        if i.get('id') not in tb_forward_users:
            i['_type'] = 'dialog'
            tb_forward_users[i.get('id')] = i

    log.debug('< updated dialog list')

    STORAGE.set('f', tb_forward_users)
    log.debug('< forwarded users: %s' % STORAGE.get('f'))

    return


def update_dialog_list():
    while True:
        try:
            _update_dialog_list()
        except TypeError:
            pass

        time.sleep(TB_UPDATE_DIALOG_LIST_INTERVAL)

    return


def forward(msg):
    for i in STORAGE.get('f', dict()).values():
        SENDER.fwd(i.get('print_name'), msg.get('id'))

    return


def _watch_dialogs():
    found = dict()
    for k, v in STORAGE.get('d').items():
        updated = v.get('_updated')
        if updated is None:
            continue

        suplus = updated + TB_INTERVAL_RESPONSE_IDLE_DIALOG
        if time.time() < suplus:
            continue

        found[k] = v

    if not found:
        return

    # load message
    messages = dict()
    for i in MESSAGES:
        message_file = os.path.join(TB_MESSAGES_DIRECTORY, '%s.txt' % i)
        if not os.path.isfile(message_file):
            continue

        messages[i] = file(message_file).read().strip()

    # send message
    for k, v in found.items():
        # set message type
        if v['_updated'] == v.get('_created'):
            message_type = 'new'
        else:
            message_type = 'idle'

        message = messages.get(message_type)
        if not message:
            continue

        SENDER.send_msg(v.get('cmd'), message.decode('utf-8'))
        d = STORAGE.get('d')
        d[k]['_updated'] = None
        STORAGE.set('d', d)

    return


def watch_dialogs():
    while True:
        time.sleep(2)

        _watch_dialogs()

    return


@coroutine
def handle_messages(*a, **kw):
    try:
        while True:
            msg = yield
            if msg.event in ('online-status',):
                continue

            when = None
            if hasattr(msg, 'date'):
                when = datetime.datetime.fromtimestamp(msg.date)
            elif hasattr(msg, 'when'):
                when = datetime.datetime.strptime(msg.when, '%Y-%m-%d %H:%M:%S')

            if msg.event not in ('message',):
                continue

            if hasattr(msg, 'peer') and msg.peer is None:  # owner message
                continue

            if hasattr(msg, 'sender') and msg.sender is not None and msg.sender.get('username') == DATA['me'].get('username'):  # me
                continue

            log.debug('got message: %s [%s]: %s' % (when, msg.event, msg))

            SENDER.mark_read(msg.peer.cmd)
            SENDER.mark_read(msg.receiver.cmd)

            now = time.time()
            o = msg.sender.copy()
            if msg.sender.cmd not in STORAGE.get('d'):
                o['_created'] = now

            o['_updated'] = now
            d = STORAGE.get('d')
            d[msg.sender.cmd] = o
            STORAGE.set('d', d)

            forward(msg)
    except GeneratorExit:
        pass
    except KeyboardInterrupt:
        RECEIVER.stop()
        log.info("exiting")


def run():
    connect()

    DATA['me'] = SENDER.get_self()

    contacts_list_thread = threading.Thread(name="contacts", target=update_contact_list, args=())
    contacts_list_thread.daemon = True
    contacts_list_thread.start()

    dialog_list_thread = threading.Thread(name="dialogs", target=update_dialog_list, args=())
    dialog_list_thread.daemon = True
    dialog_list_thread.start()

    watch_dialogs_thread = threading.Thread(name="watch dialog", target=watch_dialogs, args=())
    watch_dialogs_thread.daemon = True
    watch_dialogs_thread.start()

    RECEIVER.start()  # start the Connector.
    RECEIVER.message(handle_messages(RECEIVER))
