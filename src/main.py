#!/usr/bin/python3
import time, signal
from datetime import datetime
from logbook import INFO, NOTICE, WARNING
from CASlib import Config, Logger, RedisMB
import RPi.GPIO as GPIO


class redis2local:
    logger = None

    def __init__(self):
        self.logger = Logger.Logger(self.__class__.__name__).getLogger()
        self.config = Config.Config().getConfig()
        if "gpio" not in self.config:
            raise LookupError('Could not found gpio in config')
        if "led" not in self.config["gpio"]:
            raise LookupError('Could not found led in gpio config')

        self.redisMB = RedisMB.RedisMB()
        self.thread = None
        signal.signal(signal.SIGTERM, self.signalhandler)
        signal.signal(signal.SIGHUP, self.signalhandler)

    def log(self, level, log, zvei="No ZVEI"):
        self.logger.log(level, "[{}]: {}".format(zvei, log))

    def signalhandler(self, signum, frame):
        self.log(INFO, 'Signal handler called with signal {}'.format(signum))
        try:
            if self.thread is not None:
                self.thread.kill()
            self.redisMB.exit()
        except:
            pass
        self.log(NOTICE, 'exiting...')
        exit()

    def newAlert(self, data):
        message = self.redisMB.decodeMessage(data)
        zvei = message['zvei']
        self.log(INFO, "Received alarm. UUID: {} (Time: {}) Starting...".format(message['uuid'], str(datetime.now().time())), zvei)

        trigger = self.getAlertFromConfig(zvei)
        if not trigger:
            self.log(WARNING, "Received alarm not in config. Different config for the modules?! Stopping...", zvei)
            return

        self.log(INFO, "Start alarm tasks...", zvei)
        self.doAlertThings(zvei)
        return

    def getAlertFromConfig(self, zvei):
        for key, config in self.config['trigger'].items():
            if key == zvei:
                return config
        return False

    def doAlertThings(self, zvei):
        localactions = self.config["localaction"]
        for la in localactions:
            if la["type"] == "relay":
                self.log(INFO,
                         "Executing local action: {}".format(la["name"]),
                         zvei)
                pin = self.config["gpio"]["relay"][la["conf"]["relay"]]
                GPIO.output(pin, True)
                time.sleep(la["conf"]["time"])
                GPIO.output(pin, False)
        return

    def main(self):
        self.log(INFO, "starting...")
        self.logger.info("Setting up GPIO pins")
        for relay in self.config["gpio"]["relay"]:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(relay, GPIO.OUT, initial=False)
        try:
            self.thread = self.redisMB.subscribeToType("alertZVEI", self.newAlert)
            self.thread.join()
        except KeyboardInterrupt:
            self.signalhandler("KeyboardInterrupt", None)


if __name__ == '__main__':
    c = redis2local()
    c.main()
