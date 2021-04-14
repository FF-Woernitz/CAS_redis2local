#!/usr/bin/python3
import signal
import time

import RPi.GPIO as GPIO
from CASlibrary import Config, Logger, RedisMB


class ConfigException(Exception):
    pass


class redis2local:
    logger = None

    def __init__(self):
        self.logger = Logger.Logger(self.__class__.__name__).getLogger()
        self.config = Config.Config().getConfig()

        self.configCheck()

        self.redisMB = RedisMB.RedisMB()
        self.thread = None
        signal.signal(signal.SIGTERM, self.signalhandler)
        signal.signal(signal.SIGHUP, self.signalhandler)

    def configCheck(self):
        if "gpio" not in self.config:
            raise ConfigException('Could not found gpio key in config')
        if "relay" not in self.config["gpio"]:
            raise ConfigException('Could not found relay key in gpio config')

        if "action" not in self.config:
            raise ConfigException("No key action in config")
        if type(self.config["action"]) != dict:
            raise ConfigException("Key action in config has the wrong type")
        if len(self.config["action"]) == 0:
            raise ConfigException("No actions defined in config")
        for key, action in self.config["action"].items():
            if "name" not in action:
                raise ConfigException(f"Action {key} does not have a name")
            if "type" not in action:
                raise ConfigException(f"Action {action['name']} ({key}) has no type")
            if action["type"].lower() != "local":
                break
            if "data" not in action:
                raise ConfigException(f"Action {action['name']} ({key}) has data key")
            if "relay" not in action['data']:
                raise ConfigException(f"Action {action['name']} ({key}) has no relay")
            if "time" not in action['data']:
                raise ConfigException(f"Action {action['name']} ({key}) has no sleep time")
            if action['data']['relay'] not in self.config['gpio']['relay']:
                raise ConfigException(f"Relay of action {action['name']} ({key}) not found in gpio relay config")

    def signalhandler(self, signum, frame):
        self.logger.info('Signal handler called with signal {}'.format(signum))
        try:
            if self.thread is not None:
                self.thread.kill()
            self.redisMB.exit()
        except:
            pass
        self.logger.notice('exiting...')
        exit()

    def messageHandler(self, data):
        message = self.redisMB.decodeMessage(data)
        self.logger.debug("Received message: {}".format(message))
        action = message['message']['action']
        for configActionKey, configAction in self.config["action"].values():
            self.logger.debug("Check if action {} requested".format(configActionKey))
            if configActionKey.upper() == action.upper():
                self.logger.debug("Action {}, does match the requested key".format(configActionKey))
                if configAction["type"].upper() == "LOCAL":
                    self.logger.info("Executing action {}".format(configAction["name"]))
                    self.doAction(configAction, message['message']['data'])

    def doAction(self, action, param):
        relay = action["data"]["relay"]
        pin = self.config["gpio"]["relay"][relay]
        self.logger.info("Setting relay {} (Pin {}) on".format(relay, pin))
        GPIO.output(pin, True)
        self.logger.info("Wait for {} seconds".format(action["data"]["time"]))
        time.sleep(action["data"]["time"])
        self.logger.info("Setting relay {} (Pin {}) off".format(relay, pin))
        GPIO.output(pin, False)

    def main(self):
        self.logger.info("starting...")
        self.logger.info("Setting up GPIO pins")
        for k, relay in self.config["gpio"]["relay"].items():
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(relay, GPIO.OUT, initial=False)
        try:
            self.thread = self.redisMB.subscribeToType("action", self.messageHandler)
            self.thread.join()
        except KeyboardInterrupt:
            self.signalhandler("KeyboardInterrupt", None)


if __name__ == '__main__':
    c = redis2local()
    c.main()
