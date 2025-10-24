# https://medium.com/@kamilmatejuk/inside-python-colorful-logging-ad3a74442cc6

import logging


class AnsiColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        no_style = '\033[0m'
        bold = '\033[91m'
        grey = '\033[90m'
        yellow = '\033[93m'
        red = '\033[31m'
        red_light = '\033[91m'
        start_style = {
            'DEBUG': grey,
            'INFO': no_style,
            'WARNING': yellow,
            'ERROR': red,
            'CRITICAL': red_light + bold,
        }.get(record.levelname, no_style)
        end_style = no_style
        return f'{start_style}{super().format(record)}{end_style}'


def get_logger(name: str = __name__):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG) # DEBUG INFO WARNING ERROR CRITICAL
    formatter = AnsiColorFormatter('{asctime} | {levelname:<8s} | {name:<15s} | {message}', style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG) # DEBUG INFO WARNING ERROR CRITICAL
    return logger
